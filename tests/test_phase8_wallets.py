from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from memebot.events.models import (
    DomainEvent,
    TokenDiscovered,
    TokenLifecycleChanged,
    TokenTrade,
    TradeSide,
)
from memebot.models.market import LaunchVenue, MarketLifecycle, MarketValidationState
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.registry import TokenRegistry
from memebot.storage.database.wallets import WalletIntelligenceRepository

MINTS = (
    "So11111111111111111111111111111111111111112",
    "Vote111111111111111111111111111111111111111",
    "SysvarRent111111111111111111111111111111111",
)
WALLET = "11111111111111111111111111111111"
DRIVER = "ComputeBudget111111111111111111111111111111"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
NOW = datetime(2026, 8, 23, 2, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_wallet_metrics_early_entry_alpha_confidence_and_auto_discovery() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    wallets = WalletIntelligenceRepository(
        database.sessions,
        early_entry_seconds=30,
        candidate_min_launches=2,
        scored_min_launches=3,
        high_confidence_min_launches=5,
    )

    event_number = 100
    for index, mint in enumerate(MINTS):
        created_at = NOW + timedelta(minutes=index)
        await _ingest(
            registry,
            wallets,
            TokenDiscovered(
                event_id=UUID(int=event_number),
                provider="test",
                source_event_at=created_at,
                mint=mint,
                launch_venue=LaunchVenue.PUMP_FUN,
            ),
        )
        event_number += 1
        await _ingest(
            registry,
            wallets,
            _trade(event_number, mint, WALLET, created_at + timedelta(seconds=5), 1),
        )
        event_number += 1
        await _ingest(
            registry,
            wallets,
            _trade(event_number, mint, DRIVER, created_at + timedelta(seconds=20), 2),
        )
        event_number += 1

    await _ingest(
        registry,
        wallets,
        _trade(event_number, MINTS[0], WALLET, NOW + timedelta(seconds=30), 1.5, sell=True),
    )
    event_number += 1
    await _ingest(
        registry,
        wallets,
        TokenLifecycleChanged(
            event_id=UUID(int=event_number),
            provider="test",
            source_event_at=NOW + timedelta(minutes=4),
            mint=MINTS[1],
            lifecycle=MarketLifecycle.DEAD_OR_ILLIQUID,
            validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
            market=MARKET,
        ),
    )

    report = await wallets.wallet_report(WALLET)
    assert report is not None
    metrics = report["metrics"]
    assert report["status"] == "scored"
    assert report["confidence"] == "medium"
    assert metrics["sample_size"] == 3
    assert metrics["closed_samples"] == 1
    assert Decimal(metrics["median_return_percent"]) == Decimal(50)
    assert Decimal(metrics["early_entry_frequency_percent"]) == Decimal(100)
    assert Decimal(metrics["early_success_frequency_percent"]) == Decimal(100)
    assert Decimal(metrics["rug_exposure_percent"]) > 0
    assert metrics["trading_influence_enabled"] is False
    assert all(
        Decimal(item["mfe_percent"]) == Decimal(100) for item in report["recent_token_outcomes"]
    )

    seeded = await wallets.set_seed(WALLET, enabled=True, label="Research wallet")
    assert seeded["seeded"] is True
    assert seeded["tracked"] is True
    assert seeded["label"] == "Research wallet"
    assert (await wallets.ranked_wallets(limit=1, seeded_only=True))[0]["address"] == WALLET

    tracked_trade = _trade(
        event_number + 1,
        MINTS[0],
        WALLET,
        NOW + timedelta(minutes=5),
        3,
    )
    assert await registry.handle(tracked_trade)
    activity = await wallets.handle(tracked_trade)
    assert activity is not None
    assert activity["label"] == "Research wallet"
    assert activity["side"] == "buy"
    assert activity["mint"] == MINTS[0]

    tracked_report = await wallets.wallet_report(WALLET)
    assert tracked_report is not None
    assert tracked_report["portfolio"]["open_token_count"] >= 1
    assert tracked_report["recent_activity"][0]["side"] == "buy"
    await database.dispose()


@pytest.mark.asyncio
async def test_wallet_seed_validation_rejects_non_solana_address() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    wallets = WalletIntelligenceRepository(database.sessions)
    with pytest.raises(ValueError, match="invalid_solana_wallet"):
        await wallets.set_seed("not-a-wallet", enabled=True)
    await database.dispose()


@pytest.mark.asyncio
async def test_wallet_backfill_is_idempotent() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    wallets = WalletIntelligenceRepository(database.sessions)
    discovered = TokenDiscovered(
        event_id=UUID(int=900),
        provider="test",
        source_event_at=NOW,
        mint=MINTS[0],
        launch_venue=LaunchVenue.PUMP_FUN,
    )
    trade = _trade(901, MINTS[0], WALLET, NOW + timedelta(seconds=5), 1)

    assert await registry.handle(discovered)
    assert await registry.handle(trade)
    assert await wallets.backfill_existing(limit=10) == 1
    assert await wallets.backfill_existing(limit=10) == 0
    report = await wallets.wallet_report(WALLET)
    assert report is not None
    assert report["observed_trade_count"] == 1
    assert report["metrics"]["sample_size"] == 1
    await database.dispose()


@pytest.mark.asyncio
async def test_bounded_wallet_backfill_orders_pending_trades_and_recovers_late_history() -> None:
    from sqlalchemy import select

    from memebot.storage.database.models import WalletTradeObservationRecord

    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    wallets = WalletIntelligenceRepository(database.sessions)
    try:
        await registry.handle(
            TokenDiscovered(
                event_id=UUID(int=1900),
                provider="test",
                source_event_at=NOW,
                mint=MINTS[0],
                launch_venue=LaunchVenue.PUMP_FUN,
            )
        )
        for number, second in ((1903, 30), (1901, 10), (1902, 20)):
            await registry.handle(
                _trade(number, MINTS[0], WALLET, NOW + timedelta(seconds=second), 1)
            )
        assert await wallets.backfill_existing(limit=1) == 1
        async with database.sessions() as session:
            ids = list(await session.scalars(select(WalletTradeObservationRecord.event_id)))
        assert ids == [UUID(int=1901)]
        # An old source timestamp arriving later must not be skipped by a cursor.
        await registry.handle(_trade(1904, MINTS[0], WALLET, NOW + timedelta(seconds=5), 1))
        assert await wallets.backfill_existing(limit=1) == 1
        async with database.sessions() as session:
            assert await session.get(WalletTradeObservationRecord, UUID(int=1904)) is not None
        assert await wallets.backfill_existing(limit=10) == 2
        assert await wallets.backfill_existing(limit=10) == 0
    finally:
        await database.dispose()


async def _ingest(
    registry: TokenRegistry,
    wallets: WalletIntelligenceRepository,
    event: DomainEvent,
) -> None:
    assert await registry.handle(event)
    await wallets.handle(event)


def _trade(
    event_number: int,
    mint: str,
    wallet: str,
    observed_at: datetime,
    price: float,
    *,
    sell: bool = False,
) -> TokenTrade:
    token_amount = Decimal(10)
    return TokenTrade(
        event_id=UUID(int=event_number),
        provider="test",
        source_event_at=observed_at,
        mint=mint,
        signature=f"{event_number:064x}",
        side=TradeSide.SELL if sell else TradeSide.BUY,
        token_amount=token_amount,
        quote_amount=Decimal(str(price)) * token_amount,
        amounts_are_raw=True,
        quote_asset=WRAPPED_SOL_MINT,
        wallet=wallet,
        market=MARKET,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "lifecycle", [MarketLifecycle.BONDING_CURVE, MarketLifecycle.FINAL_STRETCH]
)
async def test_curve_progress_does_not_recalculate_wallets(lifecycle):
    def forbidden_session():
        raise AssertionError("curve progress must not run wallet SQL")

    repository = WalletIntelligenceRepository(forbidden_session)
    await repository.handle(
        TokenLifecycleChanged(
            provider="test",
            mint=MINTS[0],
            source_event_at=NOW,
            lifecycle=lifecycle,
            validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        )
    )


@pytest.mark.asyncio
async def test_durable_wallet_replay_and_terminal_recovery_after_restart():
    from sqlalchemy import select

    from memebot.storage.database.models import WalletTokenOutcomeRecord

    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    try:
        registry = TokenRegistry(database.sessions)
        await registry.handle(
            TokenDiscovered(
                provider="test",
                mint=MINTS[0],
                source_event_at=NOW,
                launch_venue=LaunchVenue.PUMP_FUN,
            )
        )
        await registry.handle(_trade(5001, MINTS[0], WALLET, NOW + timedelta(seconds=1), 1))
        await registry.handle(
            TokenLifecycleChanged(
                provider="test",
                mint=MINTS[0],
                source_event_at=NOW + timedelta(seconds=2),
                lifecycle=MarketLifecycle.GRADUATION,
                validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
            )
        )
        # No in-memory event queue survives: a new projector reconstructs work.
        repository = WalletIntelligenceRepository(database.sessions)
        assert await repository.backfill_existing(limit=25) == 1
        assert await repository.backfill_existing(limit=25) == 0
        await repository.reconcile_terminal_lifecycles(limit=25)
        async with database.sessions() as session:
            outcome = await session.scalar(select(WalletTokenOutcomeRecord))
            assert outcome is not None and outcome.graduated
        assert await repository.reconcile_terminal_lifecycles(limit=25) == 0
    finally:
        await database.dispose()
