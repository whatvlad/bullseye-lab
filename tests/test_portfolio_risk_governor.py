from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from memebot.core.config import Settings
from memebot.paper.models import PortfolioRiskSnapshot
from memebot.paper.risk_governor import PortfolioRiskGovernor

NOW = datetime(2026, 8, 23, 2, 0, tzinfo=UTC)
MINT = "So11111111111111111111111111111111111111112"


@pytest.mark.asyncio
async def test_large_paper_allocation_keeps_actual_daily_stop() -> None:
    settings = Settings(_env_file=None, paper_open_risk_budget_percent=Decimal(15))
    registry = AsyncMock()
    registry.paper_risk_snapshot.return_value = _state(
        initial_cash=Decimal(100), open_cost_basis=Decimal(0)
    )
    governor = PortfolioRiskGovernor(settings, registry)
    allowed = await governor.assess_entry(MINT, Decimal(40), as_of=NOW)
    assert allowed.allowed
    assert allowed.remaining_entry_capacity == 40
    registry.paper_risk_snapshot.return_value = _state(
        initial_cash=Decimal(100), open_cost_basis=Decimal(0), daily_realized_pnl=Decimal(-10)
    )
    assert (await governor.assess_entry(MINT, Decimal(10), as_of=NOW)).circuit_breaker_tripped


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        paper_max_total_exposure_percent=Decimal(25),
        paper_daily_loss_limit_percent=Decimal(5),
        paper_stop_loss_risk_reserve_percent=Decimal(30),
        paper_consecutive_loss_limit=3,
        paper_loss_cooldown_seconds=1800,
        paper_mint_reentry_cooldown_seconds=3600,
    )


def _state(**updates: object) -> PortfolioRiskSnapshot:
    values = {
        "portfolio_id": UUID(int=1),
        "initial_cash": Decimal(1000),
        "open_cost_basis": Decimal(100),
        "unrealized_pnl": Decimal(0),
        "daily_realized_pnl": Decimal(0),
        "consecutive_losses": 0,
        "last_closed_at": None,
        "mint_last_closed_at": None,
    }
    values.update(updates)
    return PortfolioRiskSnapshot(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "amount", "reason"),
    [
        (
            _state(daily_realized_pnl=Decimal(-60)),
            Decimal(10),
            "portfolio_daily_loss_limit_reached",
        ),
        (
            _state(consecutive_losses=3, last_closed_at=NOW - timedelta(minutes=5)),
            Decimal(10),
            "consecutive_loss_cooldown_active",
        ),
        (
            _state(mint_last_closed_at=NOW - timedelta(minutes=10)),
            Decimal(10),
            "mint_reentry_cooldown_active",
        ),
        (_state(open_cost_basis=Decimal(245)), Decimal(10), "portfolio_exposure_limit_reached"),
    ],
)
async def test_risk_governor_blocks_portfolio_level_hazards(
    state: PortfolioRiskSnapshot, amount: Decimal, reason: str
) -> None:
    registry = AsyncMock()
    registry.paper_risk_snapshot.return_value = state
    result = await PortfolioRiskGovernor(_settings(), registry).assess_entry(
        MINT, amount, as_of=NOW
    )

    assert result.allowed is False
    assert result.rejection_reason == reason


@pytest.mark.asyncio
async def test_risk_governor_allows_small_entry_inside_every_limit() -> None:
    registry = AsyncMock()
    registry.paper_risk_snapshot.return_value = _state()
    result = await PortfolioRiskGovernor(_settings(), registry).assess_entry(
        MINT, Decimal(20), as_of=NOW
    )

    assert result.allowed is True
    assert result.remaining_exposure_capacity == 150


@pytest.mark.asyncio
async def test_risk_governor_reserves_worst_case_loss_before_entry() -> None:
    registry = AsyncMock()
    registry.paper_risk_snapshot.return_value = _state(open_cost_basis=Decimal(150))

    result = await PortfolioRiskGovernor(_settings(), registry).assess_entry(
        MINT, Decimal(20), as_of=NOW
    )

    assert result.allowed is False
    assert result.rejection_reason == "portfolio_daily_loss_risk_budget_exhausted"
    assert result.circuit_breaker_tripped is False


@pytest.mark.asyncio
async def test_risk_governor_marks_real_equity_breach_as_circuit_breaker() -> None:
    registry = AsyncMock()
    registry.paper_risk_snapshot.return_value = _state(
        daily_realized_pnl=Decimal(-30), unrealized_pnl=Decimal(-25)
    )
    governor = PortfolioRiskGovernor(_settings(), registry)

    result = await governor.assess_entry(MINT, Decimal(10), as_of=NOW)

    assert result.allowed is False
    assert result.rejection_reason == "portfolio_daily_loss_limit_reached"
    assert result.circuit_breaker_tripped is True
    assert await governor.daily_loss_limit_reached(as_of=NOW) is True


@pytest.mark.asyncio
async def test_disabled_daily_loss_limit_never_pauses_or_budgets() -> None:
    settings = Settings(
        _env_file=None,
        paper_daily_loss_limit_enabled=False,
        paper_max_total_exposure_percent=Decimal(100),
    )
    registry = AsyncMock()
    registry.paper_risk_snapshot.return_value = _state(
        initial_cash=Decimal(100), open_cost_basis=Decimal(0), daily_realized_pnl=Decimal(-60)
    )
    governor = PortfolioRiskGovernor(settings, registry)
    result = await governor.assess_entry(MINT, Decimal(40), as_of=NOW)
    assert result.allowed and not result.circuit_breaker_tripped
    assert result.remaining_entry_capacity == 100
    assert not await governor.daily_loss_limit_reached(as_of=NOW)
