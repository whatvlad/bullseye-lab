import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest

import memebot.providers.pumpportal as pumpportal_module
from memebot.core.config import Settings
from memebot.events.models import (
    DomainEvent,
    ProviderConnectionState,
    ProviderHealthUpdated,
    TokenDiscovered,
    TokenTrade,
)
from memebot.providers.curve_calibration import CurveCalibration
from memebot.providers.pumpportal import PumpPortalDiscoveryProvider

MINT = "So11111111111111111111111111111111111111112"
CURVE = "11111111111111111111111111111111"
WALLET = "SysvarRent111111111111111111111111111111111"


@pytest.mark.asyncio
async def test_progress_uses_real_reserve_offset_and_can_decrease() -> None:
    provider = PumpPortalDiscoveryProvider(Settings(_env_file=None, pumpportal_api_key="test"))
    provider._calibrations[MINT] = CurveCalibration(100, 30, 20)
    published = []

    async def publish(event):
        published.append(event)
        return 1

    common = {"provider": "test", "source_event_at": datetime(2026, 9, 13, tzinfo=UTC)}
    await provider._publish_progress(MINT, CURVE, "a" * 64, 80, common, publish)
    await provider._publish_progress(MINT, CURVE, "b" * 64, 90, common, publish)
    assert [event.bonding_progress_percent for event in published] == [Decimal(50), Decimal(40)]


@pytest.mark.asyncio
async def test_closed_position_keeps_research_lease_but_budget_reserve_is_protected() -> None:
    provider = PumpPortalDiscoveryProvider(
        Settings(_env_file=None, pumpportal_api_key="test", pumpportal_max_trade_events_per_day=100)
    )
    provider.seed_open_position(MINT)
    await provider.unpin_closed_position(MINT)
    assert MINT in provider._research_until
    assert provider._subscriptions[MINT] < float("inf")
    provider.seed_daily_trade_usage(pumpportal_module.utc_now().date(), 100)
    await provider.observe_research(MINT)
    assert MINT not in provider._subscriptions


def test_candidate_pacing_respects_interval_without_day_long_throttling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    midnight = datetime(2026, 8, 25, tzinfo=UTC)
    current = midnight
    monkeypatch.setattr(pumpportal_module, "utc_now", lambda: current)
    provider = PumpPortalDiscoveryProvider(
        Settings(
            _env_file=None,
            pumpportal_api_key="secret",
            pumpportal_max_trade_events_per_day=5000,
            pumpportal_trade_budget_reserve_percent=10,
            pumpportal_max_trade_events_per_candidate=3,
            pumpportal_candidate_subscription_interval_seconds=30,
        )
    )

    assert provider._candidate_subscription_delay_seconds() == pytest.approx(30)
    current = midnight.replace(hour=12)
    provider.seed_daily_trade_usage(current.date(), 2250)
    assert provider._candidate_subscription_delay_seconds() == pytest.approx(30)
    provider.seed_daily_trade_usage(current.date(), 4000)
    assert provider._candidate_subscription_delay_seconds() == pytest.approx(30)


class FakeSocket:
    def __init__(self, messages: list[dict[str, object]]) -> None:
        self._messages = iter(json.dumps(item) for item in messages)
        self.sent: list[dict[str, object]] = []
        self.closed = False

    def __aiter__(self) -> AsyncIterator[str | bytes]:
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._messages)
        except StopIteration as error:
            raise StopAsyncIteration from error

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_candidate_budget_recovers_at_midnight_without_incoming_trades(monkeypatch):
    current = datetime(2026, 9, 14, 23, 59, tzinfo=UTC)
    monkeypatch.setattr(pumpportal_module, "utc_now", lambda: current)
    provider = PumpPortalDiscoveryProvider(
        Settings(
            _env_file=None,
            pumpportal_api_key="test",
            pumpportal_max_trade_events_per_day=100,
            pumpportal_trade_budget_reserve_percent=10,
        )
    )
    provider.seed_daily_trade_usage(current.date(), 90)
    socket = FakeSocket([])
    provider._candidate_queue[MINT] = (Decimal(1), pumpportal_module.monotonic())
    await provider._drain_candidates(socket)
    assert not socket.sent
    assert provider._next_budget_notice_at > 0
    current = datetime(2026, 9, 15, tzinfo=UTC)
    await provider._drain_candidates(socket)
    assert provider._trade_events_today == 0
    assert socket.sent == [{"method": "subscribeTokenTrade", "keys": [MINT]}]


@pytest.mark.asyncio
async def test_zero_daily_limit_keeps_metered_trade_stream_running():
    provider = PumpPortalDiscoveryProvider(
        Settings(
            _env_file=None,
            pumpportal_api_key="test",
            pumpportal_max_trade_events_per_day=0,
            pumpportal_max_trade_events_per_candidate=1,
        )
    )
    provider.seed_daily_trade_usage(pumpportal_module.utc_now().date(), 1_000_000)
    provider.seed_open_position(MINT)
    socket = FakeSocket([])
    published = []

    async def publish(event):
        published.append(event)
        return 1

    await provider._handle_trade(_trade("2" * 88), socket, publish)
    await provider._handle_trade(_trade("3" * 88), socket, publish)

    assert len([event for event in published if isinstance(event, TokenTrade)]) == 2
    assert provider._budget_halted is False
    assert provider._candidate_event_limit() is None


class FakeContext:
    def __init__(self, socket: FakeSocket) -> None:
        self.socket = socket

    async def __aenter__(self) -> FakeSocket:
        return self.socket

    async def __aexit__(self, *_args: object) -> None:
        return None


def _create(signature: str = "1" * 88) -> dict[str, object]:
    return {
        "signature": signature,
        "mint": MINT,
        "traderPublicKey": WALLET,
        "txType": "create",
        "bondingCurveKey": CURVE,
        "vTokensInBondingCurve": 1_073_000_000,
        "vSolInBondingCurve": 30,
        "name": "Budget Coin",
        "symbol": "BGT",
    }


def _trade(signature: str, side: str = "buy") -> dict[str, object]:
    return {
        "signature": signature,
        "mint": MINT,
        "traderPublicKey": WALLET,
        "txType": side,
        "tokenAmount": 12.5,
        "solAmount": 0.25,
        "bondingCurveKey": CURVE,
        "vTokensInBondingCurve": 1_060_000_000,
        "vSolInBondingCurve": 30.25,
    }


@pytest.mark.asyncio
async def test_pumpportal_uses_one_socket_and_normalizes_budgeted_trade() -> None:
    socket = FakeSocket([_create(), _trade("2" * 88)])
    settings = Settings(_env_file=None, pumpportal_api_key="secret")
    provider = PumpPortalDiscoveryProvider(
        settings,
        connect_factory=lambda *_args, **_kwargs: FakeContext(socket),
    )
    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        if isinstance(event, TokenTrade):
            await provider.close()
        return 1

    await provider.run(publish)

    methods = [str(item["method"]) for item in socket.sent]
    assert methods[:3] == ["subscribeNewToken", "subscribeMigration", "subscribeTokenTrade"]
    discovered = next(item for item in published if isinstance(item, TokenDiscovered))
    trade = next(item for item in published if isinstance(item, TokenTrade))
    assert discovered.mint == MINT
    assert trade.token_amount == 12_500_000
    assert trade.quote_amount == 250_000_000
    assert trade.virtual_token_reserves == 1_060_000_000_000_000
    assert trade.virtual_quote_reserves == 30_250_000_000
    assert socket.closed is True


@pytest.mark.asyncio
async def test_pumpportal_daily_trade_cap_halts_paid_messages() -> None:
    socket = FakeSocket([_create(), _trade("2" * 88), _trade("3" * 88)])
    settings = Settings(
        _env_file=None,
        pumpportal_api_key="secret",
        pumpportal_max_trade_events_per_day=1,
    )
    provider = PumpPortalDiscoveryProvider(
        settings,
        connect_factory=lambda *_args, **_kwargs: FakeContext(socket),
    )
    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        if (
            isinstance(event, ProviderHealthUpdated)
            and event.error_code == "pumpportal_daily_trade_budget_reached"
        ):
            await provider.close()
        return 1

    await provider.run(publish)

    trades = [item for item in published if isinstance(item, TokenTrade)]
    assert len(trades) == 1
    assert any(
        isinstance(item, ProviderHealthUpdated)
        and item.state == ProviderConnectionState.DEGRADED
        and item.error_code == "pumpportal_daily_trade_budget_reached"
        for item in published
    )


@pytest.mark.asyncio
async def test_pumpportal_reports_unfunded_trade_subscription() -> None:
    socket = FakeSocket([_create(), {"errors": ["Insufficient balance; fund the linked wallet"]}])
    settings = Settings(_env_file=None, pumpportal_api_key="secret")
    provider = PumpPortalDiscoveryProvider(
        settings,
        connect_factory=lambda *_args, **_kwargs: FakeContext(socket),
    )
    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        if (
            isinstance(event, ProviderHealthUpdated)
            and event.error_code == "pumpportal_trade_wallet_unfunded"
        ):
            await provider.close()
        return 1

    await provider.run(publish)

    assert any(
        isinstance(item, ProviderHealthUpdated)
        and item.error_code == "pumpportal_trade_wallet_unfunded"
        for item in published
    )


@pytest.mark.asyncio
async def test_open_position_stays_subscribed_after_candidate_event_cap() -> None:
    socket = FakeSocket([_create(), _trade("2" * 88)])
    settings = Settings(
        _env_file=None,
        pumpportal_api_key="secret",
        pumpportal_max_trade_events_per_candidate=1,
    )
    provider = PumpPortalDiscoveryProvider(
        settings,
        connect_factory=lambda *_args, **_kwargs: FakeContext(socket),
    )

    async def publish(event: DomainEvent) -> int:
        if isinstance(event, TokenTrade):
            await provider.pin_open_position(event.mint)
            await provider.close()
        return 1

    await provider.run(publish)

    methods = [str(item["method"]) for item in socket.sent]
    assert "subscribeTokenTrade" in methods
    assert "unsubscribeTokenTrade" not in methods


@pytest.mark.asyncio
async def test_restored_open_position_is_subscribed_on_connect() -> None:
    socket = FakeSocket([])
    settings = Settings(_env_file=None, pumpportal_api_key="secret")
    provider = PumpPortalDiscoveryProvider(
        settings,
        connect_factory=lambda *_args, **_kwargs: FakeContext(socket),
    )
    provider.seed_open_position(MINT)

    async def publish(event: DomainEvent) -> int:
        if (
            isinstance(event, ProviderHealthUpdated)
            and event.state == ProviderConnectionState.CONNECTED
        ):
            # An accepted socket/subscription does not prove paid stream entitlement.
            assert not event.confirmed_capabilities
            await provider.close()
        return 1

    await provider.run(publish)

    token_subscriptions = [item for item in socket.sent if item["method"] == "subscribeTokenTrade"]
    assert token_subscriptions == [{"method": "subscribeTokenTrade", "keys": [MINT]}]


@pytest.mark.asyncio
async def test_pumpportal_restores_daily_cap_across_restart() -> None:
    socket = FakeSocket([_create()])
    settings = Settings(
        _env_file=None,
        pumpportal_api_key="secret",
        pumpportal_max_trade_events_per_day=1000,
    )
    provider = PumpPortalDiscoveryProvider(
        settings,
        connect_factory=lambda *_args, **_kwargs: FakeContext(socket),
    )
    provider.seed_daily_trade_usage(datetime.now(UTC).date(), 1000)
    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        if (
            isinstance(event, ProviderHealthUpdated)
            and event.error_code == "pumpportal_daily_trade_budget_reached"
        ):
            await provider.close()
        return 1

    await provider.run(publish)

    methods = [str(item["method"]) for item in socket.sent]
    assert "subscribeTokenTrade" not in methods
    health = next(
        item
        for item in published
        if isinstance(item, ProviderHealthUpdated)
        and item.error_code == "pumpportal_daily_trade_budget_reached"
    )
    assert "token_discovery" in health.confirmed_capabilities
    assert health.unavailable_capabilities == frozenset({"token_trades"})
