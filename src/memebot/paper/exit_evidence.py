"""Bounded executable path and three mark-based shadow exits; no portfolio orders."""

from datetime import datetime
from decimal import Decimal as D
from typing import Any

from memebot.models.paper import PaperFill

from .migration_exit import migration_sell_quote
from .standard_math import sell_quote

MAX_MARKS = 2048


def _quote(fill: PaperFill, quantity: D) -> tuple[D, D]:
    state = fill.execution_state
    if state is None:
        raise ValueError("shadow requires executable bank")
    quote = (
        migration_sell_quote(state, int(quantity))
        if state.get("model") == "canonical_pumpswap_exit"
        else sell_quote(state["curve"], int(quantity), state["rates"])
    )
    raw = D(quote["gross_output"])
    unit = fill.quote_price_in_portfolio_currency / D(10**9)
    gross = D(int(raw * (1 - (fill.slippage or D(0)) / 10000))) * unit
    provider_bps = D(str(fill.execution_diagnostics.get("provider_fee_bps", 50)))
    fees = D(quote["protocol_fee"] + quote["creator_fee"] + quote.get("lp_fee", 0))
    net = gross - (fees + raw * provider_bps / 10000 + fill.network_fee_quote_raw) * unit
    return gross, net


def retain_exit_evidence(
    prior: dict[str, Any],
    fill: PaperFill,
    *,
    quantity: D,
    cost_basis: D,
    entry_price: D,
    opened_at: datetime,
) -> dict[str, Any]:
    """Called in the position's durable mark transaction; bounded history survives restart."""
    state = dict(prior.get("exit_evidence", {}))
    net = fill.gross_portfolio_amount - fill.total_fee_portfolio
    gross_return = (fill.actual_fill_price_raw / entry_price - 1) * 100
    net_return = (net / cost_basis - 1) * 100
    # A partial changes the risk basis; never compare its remaining-PnL peak to the old basis.
    segment = f"{quantity}:{cost_basis}"
    peak = (
        max(net_return, D(str(state.get("peak_net_pnl_percent", net_return))))
        if state.get("basis_segment") == segment
        else net_return
    )
    timeline = list(state.get("marks", []))
    timeline.append(
        {
            "timestamp": fill.market_observed_at.isoformat(),
            "slot": fill.state_slot,
            "quantity": str(quantity),
            "remaining_cost_basis": str(cost_basis),
            "gross_executable_sell_quote": str(fill.gross_portfolio_amount),
            "net_liquidation_value": str(net),
            "gross_price_change_percent": str(gross_return),
            "gross_pnl": str(
                quantity
                * (fill.actual_fill_price_raw - entry_price)
                / D(10**9)
                * fill.quote_price_in_portfolio_currency
            ),
            "net_pnl": str(net - cost_basis),
            "net_executable_pnl_percent": str(net_return),
            "peak_net_executable_pnl_percent": str(peak),
            "basis_segment": segment,
            "drawdown_from_executable_peak_percent": str(
                (1 - (1 + net_return / 100) / (1 + peak / 100)) * 100
            )
            if peak > -100
            else None,
            "telemetry": fill.exit_telemetry,
        }
    )
    dropped = max(0, len(timeline) - MAX_MARKS)
    state.update(
        marks=timeline[-MAX_MARKS:],
        retained_limit=MAX_MARKS,
        total_mark_count=int(state.get("total_mark_count", 0)) + 1,
        dropped_mark_count=int(state.get("dropped_mark_count", 0)) + dropped,
        basis_segment=segment,
        peak_net_pnl_percent=str(peak),
    )
    policies = dict(state.get("shadow_policies", {}))
    configs = fill.execution_diagnostics.get("shadow_policies", {})
    for name, config in configs.items():
        policy = dict(
            policies.get(name)
            or {
                "quantity": str(quantity),
                "cost_basis": str(cost_basis),
                "initial_cost_basis": str(cost_basis),
                "realized_pnl": "0",
                "partial_taken": False,
                "peak_gross_price": str(entry_price),
                "mfe_net_percent": "-100",
                "mae_net_percent": "1000000",
            }
        )
        if policy.get("closed_at"):
            continue
        try:
            q, basis = D(policy["quantity"]), D(policy["cost_basis"])
            gross, liquidation = _quote(fill, q)
        except (KeyError, ValueError, ArithmeticError):
            policy["data_quality"] = "executable_quote_unavailable"
            policies[name] = policy
            continue
        price = gross / (q * fill.quote_price_in_portfolio_currency / D(10**9))
        gross_change = (price / entry_price - 1) * 100
        peak_price = max(price, D(policy["peak_gross_price"]))
        policy["peak_gross_price"] = str(peak_price)
        risk_return = (liquidation / basis - 1) * 100
        whole_return = (
            (D(policy["realized_pnl"]) + liquidation - basis)
            / D(policy["initial_cost_basis"])
            * 100
        )
        policy["mfe_net_percent"] = str(max(whole_return, D(policy["mfe_net_percent"])))
        policy["mae_net_percent"] = str(min(whole_return, D(policy["mae_net_percent"])))
        reason = None
        fraction = D(1)
        age = (fill.market_observed_at - opened_at).total_seconds()
        peak_return = (peak_price / entry_price - 1) * 100
        width = D(str(config["width_percent"]))
        hold = int(config["max_holding_seconds"])
        if config.get("runner_enabled"):
            width = min(
                D(str(config["runner_max_width"])),
                max(D(str(config["runner_min_width"])), peak_return / 4),
            )
            if peak_return >= D(str(config["activation_percent"])):
                hold = int(config["runner_max_holding_seconds"])
        if risk_return <= -D(str(config["stop_percent"])):
            reason = "stop_loss"
        elif not policy["partial_taken"] and gross_change >= D(str(config["take_profit_percent"])):
            reason, fraction = "partial_take_profit", D(str(config["take_profit_fraction"]))
        elif peak_return >= D(str(config["activation_percent"])) and price <= peak_price * (
            1 - width / 100
        ):
            reason = "trailing_stop"
        elif (
            age >= int(config["stagnation_seconds"])
            and peak_return < D(str(config["stagnation_min_mfe_percent"]))
            and gross_change <= 0
        ):
            reason = "momentum_stagnation"
        elif age >= hold:
            reason = "maximum_holding_time"
        if reason:
            sold = D(int(q * fraction))
            try:
                _, proceeds = _quote(fill, sold)
            except (KeyError, ValueError, ArithmeticError):
                policy["data_quality"] = "partial_quote_unavailable"
                policies[name] = policy
                continue
            consumed = basis * sold / q
            policy["realized_pnl"] = str(D(policy["realized_pnl"]) + proceeds - consumed)
            policy["quantity"], policy["cost_basis"] = str(q - sold), str(basis - consumed)
            policy["partial_taken"] = True
            policy.setdefault("exits", []).append(
                {
                    "timestamp": fill.market_observed_at.isoformat(),
                    "slot": fill.state_slot,
                    "reason": reason,
                    "quantity": str(sold),
                    "net_proceeds": str(proceeds),
                }
            )
            if fraction == 1:
                policy["closed_at"] = fill.market_observed_at.isoformat()
                policy["net_return_percent"] = str(
                    D(policy["realized_pnl"]) / D(policy["initial_cost_basis"]) * 100
                )
                policy["profit_surrendered_percentage_points"] = str(
                    D(policy["mfe_net_percent"]) - D(policy["net_return_percent"])
                )
        policy["parameters"] = config
        policy["basis"] = (
            "same entry and sampled atomic marks; hypothetical fills at mark, "
            "no extra orders or latency guarantee"
        )
        policies[name] = policy
    state["shadow_policies"] = policies
    return state
