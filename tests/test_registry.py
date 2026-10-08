from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from memebot.events.models import (
    MarketFeatureSnapshotCreated,
    TokenDiscovered,
    TokenLifecycleChanged,
)
from memebot.models.market import LaunchVenue, MarketLifecycle, MarketValidationState
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import DomainEventRecord, TokenRecord
from memebot.storage.database.registry import TokenRegistry

MINT = "So11111111111111111111111111111111111111112"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"


@pytest.mark.asyncio
async def test_strategy_context_retains_original_price_provenance():
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    at = datetime.now(UTC)
    discovered = TokenDiscovered(provider="test", source_event_at=at, mint=MINT)
    await registry.handle(discovered)
    evidence = {
        "program": MARKET,
        "is_mayhem_mode": False,
        "state_quality": "INCOMPLETE",
        "invalidation_reason": "MULTI_EVENT_AMBIGUITY",
    }
    snapshot = MarketFeatureSnapshotCreated(
        provider="test",
        source_event_at=at,
        mint=MINT,
        trigger_event_id=discovered.event_id,
        windows=(),
        price_evidence=evidence,
    )
    await registry.handle(snapshot)
    hydrated, _ = await registry.strategy_context(MINT, as_of=at)
    assert hydrated is not None and hydrated.price_evidence == evidence
    await database.dispose()


@pytest.mark.asyncio
async def test_registry_deduplicates_events_and_projects_lifecycle() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    discovered = TokenDiscovered(
        provider="test",
        source_event_at=datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
        source_signature="1" * 88,
        source_slot=42,
        source_sequence=0,
        mint=MINT,
        name="Research Coin",
        launch_venue=LaunchVenue.PUMP_FUN,
    )
    lifecycle = TokenLifecycleChanged(
        provider="test",
        source_event_at=datetime(2026, 8, 22, 18, 1, tzinfo=UTC),
        source_signature="2" * 88,
        source_slot=43,
        source_sequence=0,
        mint=MINT,
        lifecycle=MarketLifecycle.FINAL_STRETCH,
        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        bonding_progress_percent=Decimal("82.5"),
        market=MARKET,
    )

    assert await registry.handle(discovered) is True
    assert await registry.handle(discovered) is False
    assert await registry.handle(lifecycle) is True
    stale_lifecycle = lifecycle.model_copy(
        update={
            "event_id": UUID("44ba2c08-b485-4efb-b758-d62b87536f90"),
            "source_slot": 41,
            "lifecycle": MarketLifecycle.BONDING_CURVE,
        }
    )
    assert await registry.handle(stale_lifecycle) is True

    async with database.sessions() as session:
        token_count = await session.scalar(select(func.count()).select_from(TokenRecord))
        event_count = await session.scalar(select(func.count()).select_from(DomainEventRecord))
    inspected = await registry.inspect_token(MINT)

    assert token_count == 1
    assert event_count == 3
    assert inspected is not None
    assert inspected["current_lifecycle"] == "final_stretch"
    assert inspected["markets"][0]["address"] == MARKET
    await database.dispose()
