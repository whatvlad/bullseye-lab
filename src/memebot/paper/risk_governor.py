from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from memebot.core.config import Settings
from memebot.storage.database.registry import TokenRegistry


@dataclass(frozen=True, slots=True)
class EntryRiskAssessment:
    allowed: bool
    rejection_reason: str | None
    remaining_exposure_capacity: Decimal
    circuit_breaker_tripped: bool = False
    remaining_entry_capacity: Decimal | None = None


class PortfolioRiskGovernor:
    """Portfolio-level paper entry gates independent of signal strategy."""

    def __init__(self, settings: Settings, registry: TokenRegistry) -> None:
        self._settings = settings
        self._registry = registry

    async def assess_entry(
        self,
        mint: str,
        requested_amount: Decimal,
        *,
        as_of: datetime,
    ) -> EntryRiskAssessment:
        state = await self._registry.paper_risk_snapshot(mint, as_of=as_of)
        if state is None:
            return EntryRiskAssessment(False, "active_paper_portfolio_not_found", Decimal(0))
        exposure_limit = (
            state.initial_cash * self._settings.paper_max_total_exposure_percent / Decimal(100)
        )
        capacity = max(Decimal(0), exposure_limit - state.open_cost_basis)
        if not state.execution_marks_valid:
            return EntryRiskAssessment(False, "open_position_execution_marks_unavailable", capacity)
        daily_pnl = state.daily_realized_pnl + state.unrealized_pnl
        daily_loss_limit = (
            state.initial_cash * self._settings.paper_daily_loss_limit_percent / Decimal(100)
        )
        if daily_pnl <= -daily_loss_limit:
            return EntryRiskAssessment(
                False,
                "portfolio_daily_loss_limit_reached",
                capacity,
                circuit_breaker_tripped=True,
            )
        if requested_amount > capacity:
            return EntryRiskAssessment(False, "portfolio_exposure_limit_reached", capacity)
        reserve_fraction = self._settings.paper_stop_loss_risk_reserve_percent / Decimal(100)
        projected_daily_pnl = (
            state.daily_realized_pnl - (state.open_cost_basis + requested_amount) * reserve_fraction
        )
        risk_budget = (
            state.initial_cash
            * (
                self._settings.paper_open_risk_budget_percent
                or self._settings.paper_daily_loss_limit_percent
            )
            / Decimal(100)
        )
        risk_capacity = max(
            Decimal(0),
            (risk_budget + state.daily_realized_pnl) / reserve_fraction
            - state.open_cost_basis
            - Decimal("0.00000001"),
        )
        if projected_daily_pnl <= -risk_budget:
            return EntryRiskAssessment(
                False,
                "portfolio_daily_loss_risk_budget_exhausted",
                capacity,
            )
        if (
            state.consecutive_losses >= self._settings.paper_consecutive_loss_limit
            and state.last_closed_at is not None
            and _aware(state.last_closed_at)
            + timedelta(seconds=self._settings.paper_loss_cooldown_seconds)
            > as_of
        ):
            return EntryRiskAssessment(False, "consecutive_loss_cooldown_active", capacity)
        if (
            state.mint_last_closed_at is not None
            and _aware(state.mint_last_closed_at)
            + timedelta(seconds=self._settings.paper_mint_reentry_cooldown_seconds)
            > as_of
        ):
            return EntryRiskAssessment(False, "mint_reentry_cooldown_active", capacity)
        return EntryRiskAssessment(
            True, None, capacity, remaining_entry_capacity=min(capacity, risk_capacity)
        )

    async def daily_loss_limit_reached(self, *, as_of: datetime) -> bool:
        state = await self._registry.paper_risk_snapshot("", as_of=as_of)
        if state is None:
            return False
        daily_pnl = state.daily_realized_pnl + state.unrealized_pnl
        limit = state.initial_cash * self._settings.paper_daily_loss_limit_percent / Decimal(100)
        return daily_pnl <= -limit


def _aware(value: datetime) -> datetime:
    return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
