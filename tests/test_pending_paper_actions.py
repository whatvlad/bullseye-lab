from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

import memebot.storage.database.pending as pending_module
from memebot.events.models import StrategyDecisionCreated
from memebot.models.strategy import (
    ScoreResult,
    StrategyDecisionAction,
    StrategyRegime,
)
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.pending import PendingPaperActionRepository
from memebot.storage.database.registry import TokenRegistry

MINT = "So11111111111111111111111111111111111111112"
NOW = datetime(2026, 8, 23, tzinfo=UTC)


@pytest.mark.asyncio
async def test_pending_action_is_persistent_and_deduplicated() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    pending = PendingPaperActionRepository(database.sessions)
    portfolio = await registry.ensure_default_paper_portfolio(
        initial_cash=Decimal(1000), currency="USDT"
    )
    decision = StrategyDecisionCreated(
        event_id=UUID(int=700),
        provider="test",
        source_event_at=NOW,
        mint=MINT,
        strategy_key="conservative",
        strategy_version_id=UUID(int=701),
        active_strategy=True,
        action=StrategyDecisionAction.ENTER_CANDIDATE,
        regime=StrategyRegime.EARLY_MOMENTUM,
        risk_event_id=UUID(int=702),
        score=ScoreResult(
            final_score=Decimal(85),
            component_completeness_percent=Decimal(100),
            components=(),
        ),
        reasons=("test",),
    )
    assert await registry.handle(decision)

    first = await pending.enqueue(
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        action="automatic_entry",
        ttl_seconds=30,
        decision_event_id=decision.event_id,
    )
    second = await pending.enqueue(
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        action="automatic_entry",
        ttl_seconds=30,
        decision_event_id=decision.event_id,
    )

    assert second.id == first.id
    assert first.is_new is True
    assert second.is_new is False
    restored = await pending.pending_for_mint(MINT, action="automatic_entry")
    assert restored is not None
    assert restored.decision == decision
    await pending.finish(restored.id, status="completed", reason="filled")
    assert await pending.pending_for_mint(MINT, action="automatic_entry") is None
    await database.dispose()


@pytest.mark.asyncio
async def test_expire_due_returns_action_once(monkeypatch: pytest.MonkeyPatch) -> None:
    current = NOW
    monkeypatch.setattr(pending_module, "utc_now", lambda: current)
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    pending = PendingPaperActionRepository(database.sessions)
    portfolio = await registry.ensure_default_paper_portfolio(
        initial_cash=Decimal(1000), currency="USDT"
    )
    action = await pending.enqueue(
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        action="manual_close",
        ttl_seconds=30,
        requested_by_user_id=123,
    )
    current = NOW.replace(second=31)

    assert await pending.pending_for_mint(MINT, action="manual_close") is None
    expired = await pending.expire_due()
    assert len(expired) == 1
    assert expired[0].id == action.id
    assert expired[0].requested_by_user_id == 123
    assert await pending.expire_due() == ()
    await database.dispose()
