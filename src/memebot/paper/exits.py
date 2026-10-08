from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from memebot.core.config import Settings
from memebot.models.paper import PositionEffect
from memebot.storage.database.control import TradingControlSnapshot

from .models import PositionSnapshot


@dataclass(frozen=True)
class ExitIntent:
    reason: str
    effect: PositionEffect
    quantity: Decimal


def exit_intent(
    position: PositionSnapshot,
    price: Decimal,
    now: datetime,
    control: TradingControlSnapshot,
    settings: Settings,
    *,
    hazard: bool = False,
    net_executable_pnl_percent: Decimal | None = None,
) -> ExitIntent | None:
    opened = (
        position.opened_at.replace(tzinfo=UTC)
        if position.opened_at.tzinfo is None
        else position.opened_at
    )
    if now < opened:
        return None
    change = (price / position.entry_price_raw - 1) * 100
    peak = max(price, position.peak_price_raw)
    peak_return = (peak / position.entry_price_raw - 1) * 100
    age = (now - opened).total_seconds()
    reason = None
    effect = PositionEffect.CLOSE
    quantity = position.token_quantity_raw
    risk_change = net_executable_pnl_percent if net_executable_pnl_percent is not None else change
    if risk_change <= -control.stop_loss_percent:
        reason = "stop_loss"
    elif hazard and change < 0:
        reason = "dump_hazard"
    elif not position.partial_take_profit_taken and change >= control.take_profit_percent:
        reason = "partial_take_profit"
        effect = PositionEffect.PARTIAL_CLOSE
        quantity *= settings.paper_take_profit_fraction
    else:
        activation = settings.paper_trailing_activation_percent
        width = control.trailing_stop_percent
        hold = control.max_holding_seconds
        if settings.paper_runner_enabled:
            activation = settings.paper_runner_trailing_activation_percent
            # Give a growing winner more room, with explicit bounded research parameters.
            width = min(
                settings.paper_runner_trailing_max_percent,
                max(settings.paper_runner_trailing_min_percent, peak_return / 4),
            )
            if peak_return >= activation:
                hold = settings.paper_runner_max_holding_seconds
        if peak_return >= activation and price <= peak * (1 - width / 100):
            reason = "trailing_stop"
        elif (
            age >= settings.paper_stagnation_exit_seconds
            and peak_return < settings.paper_stagnation_min_mfe_percent
            and change <= 0
        ):
            reason = "momentum_stagnation"
        elif age >= hold:
            reason = "maximum_holding_time"
    return ExitIntent(reason, effect, quantity) if reason is not None else None
