from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from memebot.events.models import StrategyDecisionCreated
from memebot.models.common import DataAvailability
from memebot.models.strategy import (
    ScoreComponent,
    ScoreResult,
    StrategyDecisionAction,
    StrategyRegime,
)
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import StrategyDecisionRecord
from memebot.storage.database.registry import TokenRegistry
from memebot.strategies.presets import initial_strategy_presets

MINT = "So11111111111111111111111111111111111111112"
NOW = datetime(2026, 8, 22, 23, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_strategy_configuration_and_decision_are_persisted() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    configurations = initial_strategy_presets()
    aggressive = next(item for item in configurations if item.key == "aggressive")
    await registry.ensure_strategy_configurations(configurations)
    decision = StrategyDecisionCreated(
        event_id=UUID(int=401),
        provider="bullseye_strategy_runner",
        source_event_at=NOW,
        source_slot=900,
        mint=MINT,
        strategy_key=aggressive.key,
        strategy_version_id=aggressive.version_id,
        active_strategy=True,
        action=StrategyDecisionAction.ENTER_CANDIDATE,
        regime=StrategyRegime.EARLY_MOMENTUM,
        risk_event_id=UUID(int=399),
        feature_event_id=UUID(int=400),
        score=ScoreResult(
            final_score=Decimal(82),
            component_completeness_percent=Decimal(70),
            components=(
                ScoreComponent(
                    name="momentum",
                    availability=DataAvailability.AVAILABLE,
                    score=Decimal(82),
                    configured_weight=Decimal(25),
                    normalized_weight=Decimal(100),
                    contribution=Decimal(82),
                ),
            ),
        ),
        reasons=("score_at_or_above_entry_threshold:60",),
    )

    assert await registry.handle(decision) is True
    assert await registry.handle(decision) is False

    async with database.sessions() as session:
        count = await session.scalar(select(func.count()).select_from(StrategyDecisionRecord))
    stored_configurations = await registry.strategy_configurations()
    decisions = await registry.latest_decisions(MINT, strategy_key="aggressive")

    assert count == 1
    assert len(stored_configurations) == 3
    assert sum(item["active_for_execution"] for item in stored_configurations) == 1
    assert decisions[0]["action"] == "enter_candidate"
    assert decisions[0]["components"][0]["score"] == "82"
    await database.dispose()
