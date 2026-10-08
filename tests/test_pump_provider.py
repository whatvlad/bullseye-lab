import asyncio
import base64
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from websockets.exceptions import ConnectionClosedError
from websockets.frames import Close

from memebot.core.config import Settings
from memebot.events.models import (
    DomainEvent,
    ProviderConnectionState,
    ProviderHealthUpdated,
    TokenDiscovered,
    TokenLifecycleChanged,
    TokenTrade,
)
from memebot.providers.solana.base import RpcAccount, RpcHealth
from memebot.providers.solana.encoding import encode_base58
from memebot.providers.solana.pump import PumpDiscoveryProvider, StreamBufferOverflow
from memebot.providers.solana.pump_idl import (
    BONDING_CURVE_ACCOUNT_DISCRIMINATOR,
    CREATE_EVENT_DISCRIMINATOR,
    PUMP_PROGRAM_ID,
    PumpSwapTrade,
)


def _number(value: int, size: int, *, signed: bool = False) -> bytes:
    return value.to_bytes(size, "little", signed=signed)


def _string(value: str) -> bytes:
    encoded = value.encode()
    return _number(len(encoded), 4) + encoded


def _key(seed: int) -> tuple[bytes, str]:
    raw = bytes([seed]) * 32
    return raw, encode_base58(raw)


class FakeRpc:
    def __init__(self, account: RpcAccount | None = None) -> None:
        self.account = account
        self.closed = False

    async def health(self) -> RpcHealth:
        return RpcHealth(
            healthy=True,
            checked_at=datetime.now(UTC),
            latency_ms=1,
        )

    async def get_account(self, _address: str, _commitment: str) -> RpcAccount | None:
        return self.account

    async def get_transaction(self, _signature: str, _commitment: str):
        return None

    async def close(self) -> None:
        self.closed = True


class FakeSocket:
    def __init__(self, messages: list[str]) -> None:
        self.messages = iter(messages)
        self.sent: list[str] = []
        self.closed = False

    def __aiter__(self) -> AsyncIterator[str | bytes]:
        return self

    async def __anext__(self) -> str:
        try:
            return next(self.messages)
        except StopIteration as error:
            raise StopAsyncIteration from error

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, socket: FakeSocket | None = None, error: Exception | None = None) -> None:
        self.socket = socket
        self.error = error

    async def __aenter__(self) -> FakeSocket:
        if self.error:
            raise self.error
        assert self.socket is not None
        return self.socket

    async def __aexit__(self, *_args: object) -> None:
        return None


def _create_fixture() -> tuple[bytes, RpcAccount]:
    mint, _ = _key(1)
    curve, curve_text = _key(2)
    user, _ = _key(3)
    creator, creator_text = _key(4)
    token_program, _ = _key(5)
    quote, quote_text = _key(6)
    event = b"".join(
        [
            CREATE_EVENT_DISCRIMINATOR,
            _string("Research Coin"),
            _string("RCH"),
            _string("https://example.invalid/meta"),
            mint,
            curve,
            user,
            creator,
            _number(1_777_000_000, 8, signed=True),
            _number(1000, 8),
            _number(2000, 8),
            _number(3000, 8),
            _number(4000, 8),
            token_program,
            b"\x00\x00",
            quote,
            _number(2000, 8),
        ]
    )
    account_data = b"".join(
        [
            BONDING_CURVE_ACCOUNT_DISCRIMINATOR,
            _number(1000, 8),
            _number(2000, 8),
            _number(3000, 8),
            _number(400, 8),
            _number(4000, 8),
            b"\x00",
            creator,
            b"\x00\x00",
            quote,
        ]
    )
    account = RpcAccount(
        address=curve_text,
        slot=42,
        owner=PUMP_PROGRAM_ID,
        lamports=1,
        executable=False,
        data_base64=base64.b64encode(account_data).decode(),
    )
    assert creator_text and quote_text
    return event, account


@pytest.mark.asyncio
async def test_provider_subscribes_normalizes_validates_and_closes() -> None:
    event_data, account = _create_fixture()
    signature = "1" * 88
    notification = {
        "jsonrpc": "2.0",
        "method": "logsNotification",
        "params": {
            "result": {
                "context": {"slot": 42},
                "value": {
                    "signature": signature,
                    "err": None,
                    "logs": [
                        f"Program {PUMP_PROGRAM_ID} invoke [1]",
                        f"Program data: {base64.b64encode(event_data).decode()}",
                        f"Program {PUMP_PROGRAM_ID} success",
                    ],
                },
            }
        },
    }
    socket = FakeSocket(
        [
            json.dumps({"jsonrpc": "2.0", "id": 1, "result": 10}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "result": 11}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "result": 12}),
            json.dumps(notification),
        ]
    )
    rpc = FakeRpc(account)
    settings = Settings(_env_file=None, solana_account_retry_count=1)
    provider = PumpDiscoveryProvider(
        settings,
        rpc,
        connect_factory=lambda *_args, **_kwargs: FakeContext(socket),
        jitter=lambda: 0,
    )
    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        if isinstance(event, TokenLifecycleChanged):
            await provider.close()
        return 1

    await provider.run(publish)

    assert len(socket.sent) == 2
    assert any(isinstance(event, TokenDiscovered) for event in published)
    lifecycle = next(event for event in published if isinstance(event, TokenLifecycleChanged))
    assert lifecycle.validation_state.value == "verified_market_data"
    assert rpc.closed is True


@pytest.mark.asyncio
async def test_provider_reconnects_after_connection_failure() -> None:
    socket = FakeSocket(
        [
            json.dumps({"jsonrpc": "2.0", "id": 1, "result": 10}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "result": 11}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "result": 12}),
        ]
    )
    contexts = iter([FakeContext(error=OSError("offline")), FakeContext(socket)])
    delays: list[float] = []
    settings = Settings(
        _env_file=None,
        solana_reconnect_base_seconds=0.01,
        solana_reconnect_jitter_seconds=0,
    )
    rpc = FakeRpc()
    provider = PumpDiscoveryProvider(
        settings,
        rpc,
        connect_factory=lambda *_args, **_kwargs: next(contexts),
        sleep=lambda delay: _record_delay(delays, delay),
        jitter=lambda: 0,
    )
    health_states: list[ProviderConnectionState] = []

    async def publish(event: DomainEvent) -> int:
        if isinstance(event, ProviderHealthUpdated):
            health_states.append(event.state)
            if event.state == ProviderConnectionState.CONNECTED:
                await provider.close()
        return 1

    await provider.run(publish)

    assert delays == [0.01]
    assert ProviderConnectionState.DEGRADED in health_states
    assert ProviderConnectionState.CONNECTED in health_states
    assert health_states[-1] == ProviderConnectionState.DISCONNECTED


@pytest.mark.asyncio
async def test_invalid_status_opens_circuit_and_suppresses_health_flood() -> None:
    class InvalidStatus(Exception):
        pass

    contexts = iter([FakeContext(error=InvalidStatus()) for _ in range(4)])
    delays: list[float] = []
    settings = Settings(
        _env_file=None,
        solana_invalid_status_halt_threshold=3,
        solana_halted_probe_seconds=900,
        solana_reconnect_base_seconds=0.01,
        solana_reconnect_jitter_seconds=0,
    )
    provider = PumpDiscoveryProvider(
        settings,
        FakeRpc(),
        connect_factory=lambda *_args, **_kwargs: next(contexts),
        jitter=lambda: 0,
    )
    health: list[ProviderHealthUpdated] = []

    async def publish(event: DomainEvent) -> int:
        if isinstance(event, ProviderHealthUpdated):
            health.append(event)
        return 1

    async def sleep(delay: float) -> None:
        delays.append(delay)
        if len(delays) == 4:
            await provider.close()

    provider._sleep = sleep
    await provider.run(publish)

    assert delays[-2:] == [900, 900]
    degraded = [item for item in health if item.state == ProviderConnectionState.DEGRADED]
    assert [item.error_code for item in degraded] == ["InvalidStatus", "rpc_service_halted"]


@pytest.mark.asyncio
@pytest.mark.parametrize("open_position", [False, True])
async def test_seeded_pump_swap_pool_only_publishes_for_exit_watch(open_position) -> None:
    settings = Settings(_env_file=None)
    provider = PumpDiscoveryProvider(settings, FakeRpc())
    pool = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
    mint = "So11111111111111111111111111111111111111112"
    quote = "11111111111111111111111111111111"
    user = "SysvarRent111111111111111111111111111111111"
    provider.seed_pump_swap_pool(pool, mint, quote)
    if open_position:
        provider.seed_open_position(mint)
    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        return 1

    await provider._normalize_and_publish(
        PumpSwapTrade(
            timestamp=1_777_000_000,
            pool=pool,
            user=user,
            is_buy=True,
            base_amount=100,
            quote_amount=250,
            pool_base_token_reserves=1_000,
            pool_quote_token_reserves=2_000,
            virtual_quote_reserves=10,
        ),
        signature="3" * 88,
        slot=600,
        ordinal=0,
        received_at=datetime(2026, 8, 22, 21, 0, tzinfo=UTC),
        publish=publish,
    )

    if not open_position:
        assert published == []
        assert pool in provider.state_tracker.states
        return
    trade = published[0]
    assert isinstance(trade, TokenTrade)
    assert trade.mint == mint
    assert trade.market == pool
    assert trade.token_amount == 100
    assert trade.quote_amount == 250
    assert trade.virtual_quote_reserves == 10


async def _record_delay(delays: list[float], delay: float) -> None:
    delays.append(delay)


@pytest.mark.asyncio
@pytest.mark.parametrize("status,expected_delay", [(429, 120), (403, 900)])
async def test_ws_handshake_status_is_recorded_and_backoff_honored(
    status: int,
    expected_delay: int,
) -> None:
    from types import SimpleNamespace

    class InvalidStatus(Exception):
        response = SimpleNamespace(status_code=status, headers={"Retry-After": "120"})

    provider = PumpDiscoveryProvider(
        Settings(_env_file=None),
        FakeRpc(),
        connect_factory=lambda *_args, **_kwargs: FakeContext(error=InvalidStatus()),
        jitter=lambda: 0,
    )
    events = []
    delays = []

    async def publish(event: DomainEvent) -> int:
        events.append(event)
        return 1

    async def sleep(delay: float) -> None:
        delays.append(delay)
        await provider.close()

    provider._sleep = sleep
    await provider.run(publish)
    assert delays == [expected_delay]
    health = next(event for event in events if isinstance(event, ProviderHealthUpdated))
    assert health.http_status == status
    assert health.rate_limited is (status == 429)


@pytest.mark.asyncio
async def test_slow_processing_does_not_block_receive_and_retains_order_and_receipt():
    gate = asyncio.Event()
    entered = asyncio.Event()
    records = []

    class SlowProvider(PumpDiscoveryProvider):
        async def _handle_notification(self, message, publish, *, received_at=None):
            if not records:
                entered.set()
                await gate.wait()
            records.append((message["sequence"], received_at, datetime.now(UTC)))

    socket = FakeSocket(
        [json.dumps({"method": "logsNotification", "sequence": i}) for i in range(10)]
    )
    provider = SlowProvider(Settings(_env_file=None), FakeRpc())

    async def publish(event):
        return 1

    task = asyncio.create_task(provider._consume(socket, publish))
    try:
        await asyncio.wait_for(entered.wait(), 1)
        for _ in range(30):
            await asyncio.sleep(0)
        assert provider._received_messages == 10
        assert records == []
        await asyncio.sleep(0.02)
        gate.set()
        await asyncio.wait_for(task, 1)
        assert [record[0] for record in records] == list(range(10))
        assert all(record[1] < record[2] for record in records)
        assert (records[-1][2] - records[-1][1]).total_seconds() >= 0.02
    finally:
        gate.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_receive_overflow_invalidates_generation_and_cancels_processor(monkeypatch):
    cancelled = asyncio.Event()
    invalidations = []

    class BlockedProvider(PumpDiscoveryProvider):
        async def _handle_notification(self, message, publish, *, received_at=None):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    socket = FakeSocket([json.dumps({"method": "logsNotification"}) for _ in range(10)])
    provider = BlockedProvider(
        Settings(_env_file=None),
        FakeRpc(),
        receive_queue_capacity=2,
        connect_factory=lambda *_args, **_kwargs: FakeContext(socket),
    )
    monkeypatch.setattr(
        provider.state_tracker,
        "invalidate",
        lambda *args, **kwargs: invalidations.append((args, kwargs)),
    )
    health = []

    async def publish(event):
        health.append(event)
        if (
            isinstance(event, ProviderHealthUpdated)
            and event.state == ProviderConnectionState.DEGRADED
        ):
            await provider.close()
        return 1

    await asyncio.wait_for(provider.run(publish), 1)
    assert cancelled.is_set()
    assert invalidations[0][0][1] == "STREAM_DISCONNECT"
    assert provider._receive_queue_peak == 2
    assert any(
        isinstance(event, ProviderHealthUpdated)
        and event.error_code == StreamBufferOverflow.__name__
        for event in health
    )
    assert not any(
        task.get_name() in {"pump-socket-receive", "pump-event-process"}
        for task in asyncio.all_tasks()
    )


def test_close_diagnostics_preserve_heartbeat_evidence_without_remote_secrets():
    error = ConnectionClosedError(None, Close(1011, "keepalive ping timeout"))
    assert PumpDiscoveryProvider._close_diagnostics(error) == {
        "received_close_code": None,
        "sent_close_code": 1011,
        "close_reason": "keepalive_ping_timeout",
    }
    remote = ConnectionClosedError(Close(1008, "https://host/?api-key=SECRET"), None)
    result = PumpDiscoveryProvider._close_diagnostics(remote)
    assert result["received_close_code"] == 1008
    assert "SECRET" not in str(result)


@pytest.mark.asyncio
async def test_overlapping_subscriptions_deduplicate_only_identical_transaction_logs():
    records = []

    class CountingProvider(PumpDiscoveryProvider):
        async def _handle_notification(self, message, publish, *, received_at=None):
            records.append(message)

    def notification(slot, logs, subscription):
        return json.dumps(
            {
                "method": "logsNotification",
                "params": {
                    "subscription": subscription,
                    "result": {
                        "context": {"slot": slot},
                        "value": {"signature": "1" * 88, "err": None, "logs": logs},
                    },
                },
            }
        )

    socket = FakeSocket(
        [
            notification(10, ["original"], 1),
            notification(10, ["original"], 2),
            notification(10, ["Log truncated"], 2),
            notification(11, ["original"], 1),
        ]
    )
    provider = CountingProvider(Settings(_env_file=None), FakeRpc())

    async def publish(event):
        return 1

    await provider._consume(socket, publish)
    assert len(records) == 3
    assert provider._duplicate_messages == 1


@pytest.mark.asyncio
async def test_invalid_event_invalidates_data_without_restarting_transport(monkeypatch):
    from pydantic import ValidationError

    records = []
    invalidations = []

    class InvalidOnce(PumpDiscoveryProvider):
        async def _handle_notification(self, message, publish, *, received_at=None):
            if message["sequence"] == 0:
                raise ValidationError.from_exception_data(
                    "native",
                    [
                        {
                            "type": "greater_than",
                            "loc": ("token_amount",),
                            "input": -1,
                            "ctx": {"gt": 0},
                        }
                    ],
                )
            records.append(message["sequence"])

    provider = InvalidOnce(Settings(_env_file=None), FakeRpc())
    monkeypatch.setattr(
        provider.state_tracker, "invalidate", lambda *args, **kwargs: invalidations.append(args)
    )
    socket = FakeSocket(
        [json.dumps({"method": "logsNotification", "sequence": i}) for i in range(2)]
    )

    async def publish(event):
        return 1

    await provider._consume(socket, publish)
    assert invalidations == [(None, "INVALID_NATIVE_EVENT")]
    assert records == [1]
    assert provider._reconnect_count == 0
