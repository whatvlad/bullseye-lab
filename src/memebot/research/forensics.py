from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from memebot.core.metrics import distribution


def number(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except ArithmeticError:
        return None
    return parsed if parsed.is_finite() else None


def performance(pnls: list[Decimal], *, initial_cash: Decimal | None = None) -> dict[str, Any]:
    wins = [value for value in pnls if value > 0]
    losses = [-value for value in pnls if value < 0]
    total = sum(pnls, Decimal(0))
    equity = peak = initial_cash if initial_cash is not None else Decimal(0)
    drawdown = Decimal(0)
    for value in pnls:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "trade_count": len(pnls),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven_trades": len(pnls) - len(wins) - len(losses),
        "win_rate": Decimal(len(wins)) / len(pnls) if pnls else None,
        "net_pnl": total,
        "net_expectancy": total / len(pnls) if pnls else None,
        "average_win": sum(wins) / len(wins) if wins else None,
        "average_loss_magnitude": sum(losses) / len(losses) if losses else None,
        "median_win": median(wins) if wins else None,
        "median_loss_magnitude": median(losses) if losses else None,
        "profit_factor": sum(wins) / sum(losses) if losses else None,
        "profit_factor_undefined_no_losses": not losses,
        "realized_max_drawdown_amount": drawdown,
        "pnl_without_largest_winner": total - max(wins) if wins else total,
        "drawdown_scope": "closed-position realization order; excludes intratrade equity",
    }


def summarize_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    outcomes = data.get("trades", [])
    positions = data.get("positions", [])
    orders = data.get("filled_orders", [])
    portfolios = data.get("portfolios", [])
    by_portfolio: dict[str, Any] = {}
    outcome_ids = {row["position_id"] for row in outcomes}
    for portfolio in portfolios:
        portfolio_id = portfolio["id"]
        closed = sorted(
            [
                row
                for row in positions
                if row["portfolio_id"] == portfolio_id and row["status"] == "closed"
            ],
            key=lambda row: (row.get("closed_at") or "", row["id"]),
        )
        pnls = [value for row in closed if (value := number(row.get("realized_pnl"))) is not None]
        matching_orders = [row for row in orders if row["portfolio_id"] == portfolio_id]
        known_fees = [
            value
            for row in matching_orders
            if (value := number((row.get("fill_json") or {}).get("total_fee_portfolio")))
            is not None
        ]
        initial = number(portfolio.get("initial_cash"))
        cash = number(portfolio.get("cash_balance"))
        realized = number(portfolio.get("realized_pnl"))
        open_costs = [
            number(row.get("remaining_cost_basis"))
            for row in positions
            if row["portfolio_id"] == portfolio_id and row["status"] == "open"
        ]
        difference = None
        if (
            initial is not None
            and cash is not None
            and realized is not None
            and all(value is not None for value in open_costs)
        ):
            difference = cash + sum((v for v in open_costs if v is not None), Decimal(0))
            difference -= initial + realized
        latencies = []
        for row in matching_orders:
            if row.get("filled_at") and row.get("decision_at"):
                latency = datetime.fromisoformat(row["filled_at"]) - datetime.fromisoformat(
                    row["decision_at"]
                )
                latencies.append(latency.total_seconds() * 1000)
        by_portfolio[portfolio_id] = {
            **performance(pnls, initial_cash=initial),
            "name": portfolio["name"],
            "portfolio_id": portfolio_id,
            "cash": cash,
            "recorded_realized_pnl": realized,
            "accounting_difference": difference,
            "missing_closed_pnl": len(closed) - len(pnls),
            "closed_positions_missing_outcome": sum(row["id"] not in outcome_ids for row in closed),
            "recorded_order_fees": sum(known_fees, Decimal(0)),
            "orders_missing_fee_evidence": len(matching_orders) - len(known_fees),
            "decision_to_fill_ms": distribution(latencies),
        }
    segments: dict[str, dict[str, list[Decimal]]] = defaultdict(lambda: defaultdict(list))
    mfe: list[float] = []
    mae: list[float] = []
    holdings: list[float] = []
    for row in outcomes:
        pnl = number(row.get("realized_pnl"))
        if row.get("status") != "closed" or pnl is None:
            continue
        segments["strategy"][row.get("strategy_key") or "unknown"].append(pnl)
        segments["exit_reason"][row.get("exit_reason") or "unknown"].append(pnl)
        segments["time_of_day_utc"][datetime.fromisoformat(row["entry_at"]).strftime("%H")].append(
            pnl
        )
        score = number((row.get("score_snapshot_json") or {}).get("final_score"))
        score_bucket = str(int(score // 10) * 10) if score is not None else "unknown"
        segments["runner_score_decile"][score_bucket].append(pnl)
        for field, target in (
            ("mfe_percent", mfe),
            ("mae_percent", mae),
            ("holding_seconds", holdings),
        ):
            value = number(row.get(field))
            if value is not None:
                target.append(float(value))
    return {
        "evidence": "saved historical database extract; no current database/API query",
        "market_data_coverage": data.get("data_counts"),
        "positions": len(positions),
        "trade_outcomes": len(outcomes),
        "portfolios": by_portfolio,
        "segments": {
            name: {bucket: performance(values) for bucket, values in buckets.items()}
            for name, buckets in segments.items()
        },
        "mfe_percent_recorded": distribution(mfe),
        "mae_percent_recorded": distribution(mae),
        "holding_seconds": distribution(holdings),
        "exit_reasons": dict(Counter(row.get("exit_reason") for row in outcomes)),
        "warnings": [
            "different strategies/sizes/periods; segments are descriptive, not causal",
            "net PnL already includes recorded costs; fees are not subtracted twice",
            "MFE/MAE use observed marks, not executable liquidation quotes",
            "missing histories cannot support unbiased earlier/later-entry counterfactuals",
            "do not combine portfolio PnL into a single capital drawdown series",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline cost-aware paper loss analysis")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.snapshot.read_bytes()
    report = summarize_snapshot(json.loads(raw.decode("utf-8-sig")))
    report["input_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, default=str, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "positions": report["positions"],
                "outcomes": report["trade_outcomes"],
                "portfolios": {
                    name: {
                        key: row[key]
                        for key in ("trade_count", "net_pnl", "net_expectancy", "profit_factor")
                    }
                    for name, row in report["portfolios"].items()
                },
            },
            default=str,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
