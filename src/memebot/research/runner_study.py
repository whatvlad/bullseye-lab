"""Offline runner research. No production thresholds or trading state are changed."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import PositionEffect
from memebot.paper.execution import ExecutionPolicy, PaperFillSimulator
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.price.base import QuotePrice
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT

INCIDENT = "711ce8d0-76a8-43f9-83ec-3681b8e63fcb"
HORIZONS = (10, 30, 60, 120, 300)
WINDOWS = (1, 2, 3, 5, 8, 10, 15, 20, 30)
OFFSETS = (-5, -3, -1, 0, 1, 3, 5, 10)
SIZES = ("0.01", "0.025", "0.05", "0.1", "0.25", "0.5")
METRICS = (
    "unique_buyer_rate_acceleration_per_second2",
    "volume_acceleration_quote_raw_per_second2",
    "price_acceleration_percent_per_second2",
    "buy_sell_volume_ratio",
    "flow_imbalance",
    "transaction_rate_per_second",
    "unique_buyers",
    "largest_buyer_volume_share",
    "buyer_volume_hhi",
    "quote_reserve_velocity_raw_per_second",
    "price_change_percent",
    "price_velocity_percent_per_second",
    "volume_velocity_quote_raw_per_second",
    "buy_count",
    "sell_count",
    "buy_volume_quote_raw",
    "sell_volume_quote_raw",
    "largest_buy_quote_raw",
    "largest_sell_quote_raw",
    "latest_price_return_percent",
    "latest_sell_liquidity_fraction",
    "latest_sell_size_mad_score",
    "observation_span_seconds",
)


def num(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def stamp(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


def iso(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat()


def rows(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        for line in source:
            yield json.loads(line)


def verify_capture(source: Path) -> None:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    for name, metadata in manifest.items():
        if not isinstance(metadata, dict) or "sha256" not in metadata:
            continue
        digest = hashlib.sha256()
        with (source / f"{name}.jsonl").open("rb") as captured:
            for chunk in iter(lambda: captured.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != metadata["sha256"]:
            raise ValueError(f"Captured evidence hash mismatch: {name}")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, default=str, indent=2, allow_nan=False), encoding="utf-8")


def write_csv(path: Path, data: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in data for key in row})
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in data:
            writer.writerow(
                {key: json.dumps(v) if isinstance(v, (dict, list)) else v for key, v in row.items()}
            )


def quantiles(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "n": len(values),
        **{
            label: ordered[min(len(values) - 1, max(0, math.ceil(q * len(values)) - 1))]
            if values
            else None
            for label, q in (
                ("p10", 0.1),
                ("p25", 0.25),
                ("median", 0.5),
                ("p75", 0.75),
                ("p90", 0.9),
                ("p95", 0.95),
            )
        },
    }


def ranks(values: list[float]) -> list[float]:
    result = [0.0] * len(values)
    indices = sorted(range(len(values)), key=values.__getitem__)
    ordered = sorted(values)
    for _, group in itertools.groupby(indices, key=values.__getitem__):
        items = list(group)
        # All values equal to the first share the mean of their sorted positions.
        start = bisect.bisect_left(ordered, values[items[0]])
        rank = start + (len(items) + 1) / 2
        for index in items:
            result[index] = rank
    return result


def spearman(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 3:
        return None
    x, y = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    mx, my = sum(x) / len(x), sum(y) / len(y)
    vx, vy = sum((v - mx) ** 2 for v in x), sum((v - my) ** 2 for v in y)
    return (
        sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / math.sqrt(vx * vy)
        if vx * vy
        else None
    )


def median_difference(a: list[float], b: list[float]) -> dict[str, Any]:
    if len(a) < 5 or len(b) < 5:
        return {
            "difference_b_minus_a": median(b) - median(a) if a and b else None,
            "bootstrap_95_percent_interval": None,
        }
    rng = random.Random(20261001)
    diffs = sorted(
        median(rng.choices(b, k=len(b))) - median(rng.choices(a, k=len(a))) for _ in range(500)
    )
    return {
        "difference_b_minus_a": median(b) - median(a),
        "bootstrap_95_percent_interval": [diffs[12], diffs[487]],
    }


def perf(data: list[dict[str, Any]], field: str = "net_return_percent") -> dict[str, Any]:
    usable = [r for r in data if num(r.get(field)) is not None]
    values = [float(r[field]) for r in usable]
    wins, losses = [v for v in values if v > 0], [-v for v in values if v < 0]
    equity = peak = drawdown = 0.0
    for row in sorted(usable, key=lambda r: r.get("exit_at", r.get("t", 0))):
        equity += float(row[field])
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "N_total": len(data),
        "N_usable": len(values),
        "N_high_quality": sum(r.get("quality") == "HIGH" for r in usable),
        "unique_tokens": len({r.get("mint") for r in usable}),
        "net_expectancy_percent": sum(values) / len(values) if values else None,
        "win_rate": len(wins) / len(values) if values else None,
        "average_win_percent": sum(wins) / len(wins) if wins else None,
        "average_loss_percent": sum(losses) / len(losses) if losses else None,
        "profit_factor": sum(wins) / sum(losses) if losses else None,
        "maximum_drawdown_equal_stake_units": drawdown / 100,
        "drawdown_scope": (
            "hypothetical equal independent stakes, exit ordering; no portfolio simulation"
        ),
    }


def asof(data: list[dict[str, Any]], t: float, max_age: float = 2) -> dict[str, Any] | None:
    # Availability/ingestion order, never select a later tick or interpolate it backwards.
    index = bisect.bisect_right([r["t"] for r in data], t) - 1
    if index < 0 or t - data[index]["t"] > max_age:
        return None
    return data[index]


def extension(ticks: list[dict[str, Any]], t: float) -> dict[str, Any]:
    current = asof(ticks, t)
    result: dict[str, Any] = {}
    for seconds in (5, 10):
        base = asof(ticks, t - seconds)
        result[f"return_last_{seconds}s_percent"] = (
            (current["price"] / base["price"] - 1) * 100 if current and base else None
        )
    recent = [r for r in ticks if t - 10 <= r["t"] <= t]
    quote = sum(float(r["quote_amount_raw"]) for r in recent)
    units = sum(float(r["token_amount_raw"]) for r in recent)
    result["distance_from_observed_10s_vwap_percent"] = (
        (current["price"] / (quote / units) - 1) * 100 if current and units and quote else None
    )
    old_wallets = {
        r["wallet"] for r in ticks if r["t"] < t - 10 and r["side"] == "buy" and r.get("wallet")
    }
    recent_wallets = {r["wallet"] for r in recent if r["side"] == "buy" and r.get("wallet")}
    new_buyers = len(recent_wallets - old_wallets)
    result["new_observed_buyers_10s"] = new_buyers if recent_wallets else None
    result["price_return_per_new_buyer_10s"] = (
        result["return_last_10s_percent"] / new_buyers
        if new_buyers and result["return_last_10s_percent"] is not None
        else None
    )
    previous = [r for r in ticks if t - 20 <= r["t"] < t - 10]
    old_volume = sum(float(r["quote_amount_raw"]) for r in previous)
    volume_change = (quote / old_volume - 1) * 100 if old_volume and asof(ticks, t - 20) else None
    result["observed_volume_growth_10s_percent"] = volume_change
    result["price_return_per_volume_growth_10s"] = (
        result["return_last_10s_percent"] / volume_change
        if volume_change and result["return_last_10s_percent"] is not None
        else None
    )
    return result


def peak_label(ticks: list[dict[str, Any]], t: float, h: int) -> dict[str, Any]:
    base = asof(ticks, t)
    sample = [
        r
        for r in ticks
        if t < r["t"] <= t + h
        and base
        and r["market_address"] == base["market_address"]
        and r["quote_asset"] == base["quote_asset"]
    ]
    if not base or not sample or not base["price"]:
        return {"coverage": "missing", "peak_return_percent": None}
    end = asof(sample, t + h)
    gaps = [b["t"] - a["t"] for a, b in zip([base, *sample], sample, strict=False)]
    local_gap = max(gaps, default=0)
    return {
        "coverage": "bounded_observation" if end and local_gap <= 2 else "gappy",
        "peak_return_percent": (max(r["price"] for r in sample) / base["price"] - 1) * 100,
        "endpoint_return_percent": (end["price"] / base["price"] - 1) * 100 if end else None,
        "max_intertrade_gap_seconds": local_gap,
        "observations": len(sample),
        "quality": "MEDIUM" if end and local_gap <= 2 else "LOW",
    }


def failure_signals(f: dict[str, Any]) -> list[str]:
    m = f["metrics"]
    result = []
    if (m.get("unique_buyer_rate_acceleration_per_second2") or 0) < 0 and (
        m.get("flow_imbalance") is not None and m["flow_imbalance"] < 0
    ):
        result.append("buyer_deceleration_and_net_selling")
    if m.get("latest_price_return_percent") is not None and (
        m["latest_price_return_percent"] <= -5
        and (m.get("latest_sell_liquidity_fraction") or 0) >= 0.05
    ):
        result.append("large_sell_with_price_shock")
    if m.get("quote_reserve_velocity_raw_per_second") is not None and (
        m["quote_reserve_velocity_raw_per_second"] < 0
        and (m.get("price_velocity_percent_per_second") or 0) < 0
    ):
        result.append("reserves_and_price_falling")
    return result


def phase(f: dict[str, Any]) -> str:
    m = f["metrics"]
    ba = m.get("unique_buyer_rate_acceleration_per_second2")
    va = m.get("volume_acceleration_quote_raw_per_second2")
    pv = m.get("price_velocity_percent_per_second")
    if ba is None or va is None or pv is None:
        return "UNKNOWN"
    if failure_signals(f):
        return "DISTRIBUTION" if (m.get("flow_imbalance") or 0) < 0 else "FAILED"
    if pv > 0 and ba <= 0:
        return "OVEREXTENDED"
    if pv > 0 and ba > 0 and va > 0:
        return "EARLY_EXPANSION"
    return "IGNITION" if ba > 0 else "WATCHING"


def market_snapshot(
    row: dict[str, Any], t: float, token: dict[str, Any]
) -> ExecutionMarketSnapshot:
    def integer(key: str) -> int | None:
        return int(Decimal(str(row[key]))) if row.get(key) is not None else None

    return ExecutionMarketSnapshot(
        mint=token["mint"],
        market=row["market_address"],
        venue=LaunchVenue(token["launch_venue"]),
        lifecycle=MarketLifecycle.BONDING_CURVE,
        observed_at=datetime.fromtimestamp(row["t"], UTC),
        source_slot=row.get("source_slot"),
        observed_price_raw=Decimal(str(row["price_raw"])),
        quote_asset=row["quote_asset"],
        real_token_reserves_raw=integer("real_token_reserves"),
        real_quote_reserves_raw=integer("real_quote_reserves"),
        virtual_token_reserves_raw=integer("virtual_token_reserves"),
        virtual_quote_reserves_raw=integer("virtual_quote_reserves"),
    )


def simulate(
    ticks: list[dict[str, Any]],
    token: dict[str, Any],
    entry_t: float,
    exit_t: float,
    size: str = "0.05",
    *,
    extra_tip_sol: str = "0",
) -> dict[str, Any]:
    # Conditional round trip between TWO recorded states, not full strategy/fill replay.
    # Preserve latency; do not reach into a future tick to fill an earlier order.
    entry, exit_row = asof(ticks, entry_t + 0.8), asof(ticks, exit_t + 0.8)
    result: dict[str, Any] = {"net_return_percent": None, "quality": "LOW", "size_sol": size}
    if not entry or not exit_row:
        return {**result, "exclusion": "missing_or_stale_tick"}
    if token["launch_venue"] != "pump_fun" or entry["quote_asset"] != WRAPPED_SOL_MINT:
        return {**result, "exclusion": "unsupported_venue_or_quote"}
    if entry["market_address"] != exit_row["market_address"]:
        return {**result, "exclusion": "market_changed"}
    if any(
        r.get("real_quote_reserves") is None or r.get("real_token_reserves") is None
        for r in (entry, exit_row)
    ):
        return {**result, "exclusion": "real_reserves_unknown"}
    policy = ExecutionPolicy(
        venue_fee_bps=Decimal(125),
        latency_slippage_bps=Decimal(50),
        network_fee_sol=Decimal("0.00001"),
        priority_fee_sol=Decimal("0.0001") + Decimal(extra_tip_sol),
        compute_latency_ms=0,
        submission_latency_ms=0,
        max_market_staleness_seconds=2,
        max_quote_price_staleness_seconds=2,
    )
    simulator = PaperFillSimulator(policy)

    def quote(t: float) -> QuotePrice:
        return QuotePrice(
            quote_asset=WRAPPED_SOL_MINT,
            portfolio_currency="SOL",
            price=Decimal(1),
            provenance=ProviderProvenance(
                provider="SOL_identity_conversion",
                observed_at=datetime.fromtimestamp(t, UTC),
                confidence=DataConfidence.HIGH,
            ),
        )

    try:
        buy_t, sell_t = (
            datetime.fromtimestamp(entry_t + 0.8, UTC),
            datetime.fromtimestamp(exit_t + 0.8, UTC),
        )
        buy = simulator.simulate_buy(
            market_snapshot(entry, entry_t, token),
            quote(entry_t + 0.8),
            requested_portfolio_amount=Decimal(size),
            signal_at=buy_t,
            decision_at=buy_t,
        )
        if buy.fill is None:
            return {**result, "exclusion": buy.rejection_reason}
        # Paper ledger buy cost embeds venue fee already; add only service and network.
        cost = buy.fill.gross_portfolio_amount + (
            buy.fill.execution_provider_fee_quote_raw + buy.fill.network_fee_quote_raw
        ) / Decimal(10**9)
        sell = simulator.simulate_sell(
            market_snapshot(exit_row, exit_t, token),
            quote(exit_t + 0.8),
            token_amount_raw=buy.fill.token_amount_raw,
            position_effect=PositionEffect.CLOSE,
            exit_reason="research",
            signal_at=sell_t,
            decision_at=sell_t,
        )
        if sell.fill is None:
            return {**result, "exclusion": sell.rejection_reason}
        proceeds = sell.fill.gross_portfolio_amount - sell.fill.total_fee_portfolio
        result.update(
            net_return_percent=float((proceeds / cost - 1) * 100),
            net_pnl_sol=float(proceeds - cost),
            cost_sol=float(cost),
            max_impact_bps=float(max(buy.fill.price_impact_bps, sell.fill.price_impact_bps)),
            quality="MEDIUM",
            exclusion=None,
        )
        path = [r["t"] for r in ticks if entry["t"] <= r["t"] <= exit_row["t"]]
        if max((b - a for a, b in itertools.pairwise(path)), default=0) > 2:
            result["quality"] = "LOW"
        if result["max_impact_bps"] > 300:
            result.update(net_return_percent=None, exclusion="impact_above_research_cap_300bps")
    except (ValueError, ArithmeticError):
        result["exclusion"] = "invalid_market_state"
    return result


def analyze(source: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    tokens = {r["id"]: r for r in rows(source / "tokens.jsonl")}
    strategy_versions = {
        r["version_id"]: r["configuration_json"] for r in rows(source / "strategies.jsonl")
    }
    positions = list(rows(source / "positions.jsonl"))
    outcomes = {r["position_id"]: r for r in rows(source / "trade_outcomes.jsonl")}
    orders = list(rows(source / "orders.jsonl"))
    bought = {r["token_id"] for r in positions}
    latest = sorted(
        [r for r in positions if r["portfolio_id"] == INCIDENT],
        key=lambda r: float(r["realized_pnl"]),
    )[:2]
    worst_ids = {r["token_id"] for r in latest}
    print("Loading compact causal trades and decisions", flush=True)
    trades: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows(source / "market_trades.jsonl"):
        r["t"], r["source_t"], r["price"] = (
            stamp(r["ingested_at"]),
            stamp(r["source_event_at"]),
            num(r["price_raw"]),
        )
        if r["price"] and r["market_address"]:
            trades[r["token_id"]].append(r)
    decisions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    decision_by_id = {}
    for r in rows(source / "decisions.jsonl"):
        r["t"] = stamp(r["ingested_at"])
        decision_by_id[r["event_id"]] = r
        decisions[r["token_id"]].append(r)
    # Keep one decision per token/time. Cross-profile duplication is not independent evidence.
    first_decision = {key: min(value, key=lambda r: r["t"]) for key, value in decisions.items()}
    risk_by_feature = {}
    execution_by_decision = {}
    for r in rows(source / "decision_outcomes.jsonl"):
        execution_by_decision[r["decision_event_id"]] = {
            "execution_status": r["execution_status"],
            "execution_rejection_reason": r["execution_rejection_reason"],
        }
        f = r.get("feature_snapshot_json") or {}
        if f.get("event_id") and f["event_id"] not in risk_by_feature:
            risk = r.get("risk_snapshot_json") or {}
            evidence = {
                e["code"]: e.get("value")
                for e in risk.get("evidence", [])
                if e.get("availability") == "available"
            }
            risk_by_feature[f["event_id"]] = {
                "risk_score": num(risk.get("risk_score")),
                "risk_assessed_at": risk.get("assessed_at"),
                "holder_count": evidence.get("holder_count"),
                "creator_supply_percent": evidence.get("creator_supply_percent"),
                "top10_supply_percent": evidence.get("top10_supply_percent"),
                "smart_wallet_count": None,
                "bundled_supply_percent": None,
            }
    # Fold 3GB of feature histories by token. Retain only compact research metrics.
    features: dict[str, list[dict[str, Any]]] = defaultdict(list)
    print("Streaming and compacting feature histories", flush=True)
    for r in rows(source / "features.jsonl"):
        if r["token_id"] not in tokens:
            continue  # Feature-only launches have no exported trade/decision/position history.
        windows = r["windows_json"]
        w = next((w for w in windows if w["window_seconds"] == 10), None)
        if not w:
            continue
        t = stamp(r["ingested_at"])
        if stamp(r["observed_at"]) > t:
            continue
        r = {
            "t": t,
            "observed_t": stamp(r["observed_at"]),
            "event_id": r["event_id"],
            "token_id": r["token_id"],
            "age": t - stamp(tokens[r["token_id"]]["first_seen_at"]),
            "provider": r["provider"],
            "price": num(r["latest_price_raw"]),
            "metrics": {key: num(w.get(key)) for key in METRICS},
            "lifecycle": r["lifecycle"],
            "risk": risk_by_feature.get(r["event_id"], {}),
        }
        features[r["token_id"]].append(r)
    del risk_by_feature
    print("Calculating per-position excursions and candidate labels", flush=True)
    trade_report, timing, costs, exit_report, timeline = [], [], [], [], []
    preentry_flags = []
    for p in positions:
        token = {**tokens[p["token_id"]], "launch_venue": p["venue"]}
        ticks = trades.get(p["token_id"], [])
        entry_t, exit_t = stamp(p["opened_at"]), stamp(p["closed_at"]) if p["closed_at"] else None
        o = outcomes.get(p["id"], {})
        sample = [
            r
            for r in ticks
            if exit_t and entry_t <= r["t"] <= exit_t and r["market_address"] == p["market_address"]
        ]
        entry_price = float(p["entry_price_raw"])
        max_r = max(sample, key=lambda r: r["price"], default=None)
        min_r = min(sample, key=lambda r: r["price"], default=None)
        stamps = [entry_t, *[r["t"] for r in sample], exit_t] if exit_t else []
        gap = max((b - a for a, b in itertools.pairwise(stamps)), default=None)
        source_known = bool(sample) and all(
            "pumpportal" not in r["provider"] and r["source_slot"] for r in sample
        )
        quality = "MEDIUM" if sample and gap is not None and gap <= 2 else "LOW"
        buy_orders = [
            r
            for r in orders
            if r["token_id"] == p["token_id"]
            and r["portfolio_id"] == p["portfolio_id"]
            and r["side"] == "buy"
            and r["status"] == "filled"
            and abs(stamp(r["filled_at"]) - entry_t) < 0.01
        ]
        buy = buy_orders[0] if buy_orders else {}
        signal_entry_t = stamp(buy["decision_at"]) if buy.get("decision_at") else entry_t - 0.8
        closing_order: dict[str, Any] = next(
            (r for r in orders if r["event_id"] == o.get("exit_order_event_id")), {}
        )
        signal_exit_t = (
            stamp(closing_order["decision_at"])
            if closing_order.get("decision_at")
            else (exit_t - 0.8 if exit_t else entry_t)
        )
        decision = decision_by_id.get(buy.get("decision_event_id"), {})
        history = [r for r in ticks if r["t"] <= entry_t]
        low = min(history, key=lambda r: r["price"], default=None)
        first = history[0] if history else None
        current = asof(ticks, entry_t)
        exit_mark = asof(ticks, exit_t) if exit_t else None
        recorded_exit_price = num(o.get("expected_exit_price_raw"))
        exit_difference = (
            (recorded_exit_price / exit_mark["price"] - 1) * 100
            if (recorded_exit_price and exit_mark)
            else None
        )
        baseline_reconciled = exit_difference is not None and abs(exit_difference) <= 5

        def reconcile(
            simulation: dict[str, Any],
            exit_difference: float | None = exit_difference,
            baseline_reconciled: bool = baseline_reconciled,
        ) -> dict[str, Any]:
            simulation["recorded_exit_mark_difference_percent"] = exit_difference
            simulation["baseline_exit_reconciled_within_5_percent"] = baseline_reconciled
            if not baseline_reconciled and simulation.get("net_return_percent") is not None:
                simulation["conditional_two_state_return_percent"] = simulation[
                    "net_return_percent"
                ]
                simulation.update(
                    net_return_percent=None,
                    quality="LOW",
                    exclusion="baseline_exit_fill_unreconciled",
                )
            return simulation

        result = {
            "position_id": p["id"],
            "portfolio_id": p["portfolio_id"],
            "mint": p["mint"],
            "symbol": token["symbol"],
            "entry_at": iso(entry_t),
            "exit_at": iso(exit_t) if exit_t else None,
            "N_observed_ticks": len(sample),
            "max_intertrade_gap_seconds": gap,
            "quality": quality,
            "source_timestamp_quality": "native" if source_known else "estimated_or_unknown",
            "holder_coverage": "snapshot_only" if o.get("risk_snapshot_json") else "unknown",
            "wallet_coverage": "observed_addresses_only; profitable reputation unknown",
            "net_pnl": num(p["realized_pnl"]),
            "net_return_percent": num(o.get("pnl_percent")),
            "holding_seconds": exit_t - entry_t if exit_t else None,
            "recorded_mfe_percent": num(o.get("mfe_percent")),
            "recorded_mae_percent": num(o.get("mae_percent")),
            "observed_mfe_percent": max(0, (max_r["price"] / entry_price - 1) * 100)
            if max_r
            else None,
            "observed_mae_percent": min(0, (min_r["price"] / entry_price - 1) * 100)
            if min_r
            else None,
            "time_to_observed_mfe_seconds": max_r["t"] - entry_t
            if max_r and max_r["price"] > entry_price
            else None,
            "time_to_observed_mae_seconds": min_r["t"] - entry_t
            if min_r and min_r["price"] < entry_price
            else None,
            "entry_age_seconds": entry_t - stamp(token["first_seen_at"]),
            "return_first_observed_price_to_entry_mark_percent": (
                current["price"] / first["price"] - 1
            )
            * 100
            if current and first
            else None,
            "return_observed_low_to_entry_mark_percent": (current["price"] / low["price"] - 1) * 100
            if current and low
            else None,
            "actual_fill_vs_first_observed_price_percent": (entry_price / first["price"] - 1) * 100
            if first
            else None,
            "baseline_gap_from_discovery_seconds": first["t"] - stamp(token["first_seen_at"])
            if first
            else None,
            "entry_reasons": o.get("entry_reasons"),
            "exit_reason": o.get("exit_reason"),
            "signal_to_decision_seconds": stamp(buy["decision_at"]) - stamp(buy["signal_at"])
            if buy.get("signal_at") and buy.get("decision_at")
            else None,
            "decision_to_fill_seconds": entry_t - stamp(buy["decision_at"])
            if buy.get("decision_at")
            else None,
            "first_entry_candidate_to_fill_seconds": entry_t
            - min(
                (
                    r["t"]
                    for r in decisions.get(p["token_id"], [])
                    if r["action"] == "enter_candidate" and r["t"] <= entry_t
                ),
                default=entry_t,
            ),
            "runner_score": num(decision.get("final_score")),
            "recorded_exit_mark_difference_percent": exit_difference,
            "baseline_exit_reconciled_within_5_percent": baseline_reconciled,
        }
        trade_report.append(result)
        result.update(extension(ticks, entry_t))
        first_momentum = next(
            (
                f
                for f in features.get(p["token_id"], [])
                if f["t"] <= entry_t and phase(f) == "EARLY_EXPANSION"
            ),
            None,
        )
        momentum_tick = asof(ticks, first_momentum["t"]) if first_momentum else None
        result["first_structural_momentum_signal_at"] = (
            iso(first_momentum["t"]) if first_momentum else None
        )
        result["return_first_momentum_to_entry_mark_percent"] = (
            (current["price"] / momentum_tick["price"] - 1) * 100
            if current and momentum_tick
            else None
        )
        f_entry = o.get("feature_snapshot_json") or {}
        w_entry: dict[str, Any] = next(
            (w for w in f_entry.get("windows", []) if w["window_seconds"] == 10), {}
        )
        valid_feature = (
            bool(f_entry.get("observed_at")) and stamp(f_entry["observed_at"]) <= signal_entry_t
        )
        flags = (
            failure_signals({"metrics": {k: num(w_entry.get(k)) for k in METRICS}})
            if valid_feature
            else []
        )
        preentry_flags.append(
            {
                "position_id": p["id"],
                "mint": p["mint"],
                "net_pnl": num(p["realized_pnl"]),
                "feature_available_by_signal": valid_feature,
                "flags": flags,
            }
        )
        result["preentry_failure_flags"] = flags
        observed_creator = token.get("creator")
        creator_sells = [
            r
            for r in sample
            if observed_creator and r.get("wallet") == observed_creator and r["side"] == "sell"
        ]
        result["observed_creator_sell_count_in_position"] = (
            len(creator_sells) if observed_creator else None
        )
        result["observed_creator_sell_sol_in_position"] = (
            sum(float(r["quote_amount_raw"]) / 10**9 for r in creator_sells)
            if observed_creator
            else None
        )
        result["time_to_recorded_mae_seconds"] = (
            result["time_to_observed_mae_seconds"]
            if min_r
            and num(o.get("lowest_price_raw"))
            and abs(min_r["price"] / float(o["lowest_price_raw"]) - 1) < 0.000001
            else None
        )
        if exit_t:
            for offset in OFFSETS:
                if signal_entry_t + offset >= signal_exit_t:
                    simulation = {
                        "net_return_percent": None,
                        "exclusion": "entry_after_exit",
                        "quality": "LOW",
                    }
                else:
                    simulation = simulate(ticks, token, signal_entry_t + offset, signal_exit_t)
                simulation = reconcile(simulation)
                timing.append(
                    {
                        "position_id": p["id"],
                        "mint": p["mint"],
                        "offset_seconds": offset,
                        "exit_at": exit_t,
                        **simulation,
                    }
                )
            for size in SIZES:
                costs.append(
                    {
                        "position_id": p["id"],
                        "mint": p["mint"],
                        "exit_at": exit_t,
                        **reconcile(simulate(ticks, token, signal_entry_t, signal_exit_t, size)),
                    }
                )
            costs.append(
                {
                    "position_id": p["id"],
                    "mint": p["mint"],
                    "exit_at": exit_t,
                    "scenario": "additional_0.0001_SOL_tip_each_side",
                    **reconcile(
                        simulate(
                            ticks,
                            token,
                            signal_entry_t,
                            signal_exit_t,
                            "0.05",
                            extra_tip_sol="0.0001",
                        )
                    ),
                }
            )
        position_features = [
            r
            for r in features.get(p["token_id"], [])
            if exit_t and entry_t <= r["t"] <= exit_t and r["t"] - r["observed_t"] <= 2
        ]
        for signal in (
            "buyer_deceleration_and_net_selling",
            "large_sell_with_price_shock",
            "reserves_and_price_falling",
        ):
            match = next((r for r in position_features if signal in failure_signals(r)), None)
            if match and exit_t:
                simulation = simulate(ticks, token, signal_entry_t, match["t"])
                baseline = simulate(ticks, token, signal_entry_t, signal_exit_t)
                delta = (
                    simulation["net_return_percent"] - baseline["net_return_percent"]
                    if simulation["net_return_percent"] is not None
                    and baseline["net_return_percent"] is not None
                    else None
                )
                if not baseline_reconciled:
                    delta = None
            else:
                simulation, delta = {}, None
            exit_report.append(
                {
                    "position_id": p["id"],
                    "mint": p["mint"],
                    "signal": signal,
                    "first_observed_at": iso(match["t"]) if match else None,
                    "seconds_before_exit": exit_t - match["t"] if match and exit_t else None,
                    "conditional_avoided_return_points": delta,
                    "actual_net_pnl": num(p["realized_pnl"]),
                    **simulation,
                }
            )
        if p["token_id"] in worst_ids and p["portfolio_id"] == INCIDENT:
            # Every observed feature / decision / quote / order, not forward-filled checkpoints.
            discovery = stamp(token["first_seen_at"])
            timeline.append(
                {"mint": p["mint"], "t": discovery, "T_plus_seconds": 0, "kind": "discovery"}
            )
            for f in features.get(p["token_id"], []):
                if exit_t and f["t"] <= exit_t + 1:
                    prior = asof(ticks, f["t"])
                    ds = asof(decisions.get(p["token_id"], []), f["t"], max_age=60)
                    timeline.append(
                        {
                            "mint": p["mint"],
                            "t": f["t"],
                            "T_plus_seconds": f["t"] - discovery,
                            "kind": "observation",
                            "phase_research": phase(f),
                            "price_raw": f["price"],
                            "market_cap_sol_assumed_1b_supply": f["price"] * 10**6
                            if f["price"]
                            else None,
                            "real_quote_liquidity_sol": float(prior["real_quote_reserves"]) / 10**9
                            if prior and num(prior.get("real_quote_reserves")) is not None
                            else None,
                            "runner_score": num(ds.get("final_score")) if ds else None,
                            "risk_snapshot": f["risk"],
                            "risk_snapshot_causal_at_this_time": bool(
                                f["risk"].get("risk_assessed_at")
                                and stamp(f["risk"]["risk_assessed_at"]) <= f["t"]
                            ),
                            "organic_score": None,
                            "failure_signals": failure_signals(f),
                            **f["metrics"],
                        }
                    )
            for d in decisions.get(p["token_id"], []):
                if exit_t and d["t"] <= exit_t:
                    timeline.append(
                        {
                            "mint": p["mint"],
                            "t": d["t"],
                            "T_plus_seconds": d["t"] - discovery,
                            "kind": "decision",
                            "strategy": d["strategy_key"],
                            "action": d["action"],
                            "runner_score": num(d["final_score"]),
                            "reasons": d["reasons"],
                            "feature_event_id": d["feature_event_id"],
                            "risk_event_id": d["risk_event_id"],
                        }
                    )
            for r in orders:
                if r["mint"] == p["mint"] and r["portfolio_id"] == INCIDENT:
                    for field in ("signal_at", "decision_at", "submitted_at", "filled_at"):
                        if r.get(field):
                            timeline.append(
                                {
                                    "mint": p["mint"],
                                    "t": stamp(r[field]),
                                    "T_plus_seconds": stamp(r[field]) - discovery,
                                    "kind": r["side"] + ":" + field,
                                    "order_event_id": r["event_id"],
                                    "status": r["status"],
                                    "exit_reason": r["exit_reason"],
                                    "fill": r["fill_json"],
                                    "rejection_reason": r["rejection_reason"],
                                }
                            )
                    if r.get("fill_json"):
                        fill = r["fill_json"]
                        for field in ("market_observed_at", "quote_price_observed_at"):
                            if fill.get(field):
                                timeline.append(
                                    {
                                        "mint": p["mint"],
                                        "t": stamp(fill[field]),
                                        "T_plus_seconds": stamp(fill[field]) - discovery,
                                        "kind": r["side"] + ":" + field,
                                        "order_event_id": r["event_id"],
                                        "note": "SOL/USD conversion timestamp"
                                        if field.startswith("quote")
                                        else "RPC execution reserve snapshot",
                                    }
                                )
            for label, tick in (("observed_MFE", max_r), ("observed_MAE", min_r)):
                if tick:
                    timeline.append(
                        {
                            "mint": p["mint"],
                            "t": tick["t"],
                            "T_plus_seconds": tick["t"] - discovery,
                            "kind": label,
                            "price_raw": tick["price"],
                            "source_event_id": tick["event_id"],
                        }
                    )
    print("Calculating missed-runner, equivalent-age and observation-window studies", flush=True)
    missed, labels, observations, cohorts = [], [], [], []
    for token_id, ticks in trades.items():
        token = tokens[token_id]
        discovery = stamp(token["first_seen_at"])
        first_d = first_decision.get(token_id)
        anchor = first_d["t"] if first_d else ticks[0]["t"]
        anchor_labels = {str(h): peak_label(ticks, anchor, h) for h in HORIZONS}
        row = {
            "mint": token["mint"],
            "symbol": token["symbol"],
            "bought": token_id in bought,
            "anchor_at": iso(anchor),
            "anchor_age_seconds": anchor - discovery,
            "anchor_type": "first_recorded_decision" if first_d else "first_recorded_trade",
            "first_decision_reasons": first_d["reasons"] if first_d else None,
            "first_decision_action": first_d["action"] if first_d else None,
            "forward_peak_labels": anchor_labels,
        }
        row["quality"] = (
            "MEDIUM"
            if any(v["coverage"] == "bounded_observation" for v in anchor_labels.values())
            else "LOW"
        )
        row["source_timestamp_quality"] = (
            "estimated_or_unknown"
            if any("pumpportal" in r["provider"] for r in ticks)
            else "native_source"
        )
        row["first_decisions_by_strategy"] = [
            {
                "strategy": strategy,
                "t": iso(first["t"]),
                "age_seconds": first["t"] - discovery,
                "action": first["action"],
                "reasons": first["reasons"],
                "score": num(first["final_score"]),
                "strategy_version_id": first["strategy_version_id"],
                "configuration_thresholds": {
                    k: v
                    for k, v in strategy_versions.get(first["strategy_version_id"], {}).items()
                    if k not in {"component_weights", "display_name", "version_id"}
                },
                **execution_by_decision.get(first["event_id"], {}),
            }
            for strategy in sorted({d["strategy_key"] for d in decisions.get(token_id, [])})
            for first in [next(d for d in decisions[token_id] if d["strategy_key"] == strategy)]
        ]
        labels.append(row)
        if token_id not in bought and any(
            v["coverage"] == "bounded_observation"
            and v["peak_return_percent"] >= (50 if h == "300" else 25)
            for h, v in anchor_labels.items()
        ):
            missed.append(row)
        for age in WINDOWS:
            age_feature = asof(features.get(token_id, []), discovery + age)
            if age_feature is None or discovery + age - age_feature["observed_t"] > 2:
                observations.append(
                    {
                        "mint": token["mint"],
                        "window_seconds": age,
                        "quality": "LOW",
                        "net_return_percent": None,
                        "exclusion": "no_causal_fresh_feature",
                    }
                )
                continue
            future = peak_label(ticks, discovery + age, 60)
            simulated = simulate(ticks, token, discovery + age, discovery + age + 60)
            observations.append(
                {
                    "mint": token["mint"],
                    "window_seconds": age,
                    "feature_event_id": age_feature["event_id"],
                    "future_peak": future,
                    **simulated,
                }
            )
        # One token at each fixed age; same 10-second window, not bought-at-100s vs skipped-at-3s.
        for age in (10, 20, 30, 60):
            age_feature = asof(features.get(token_id, []), discovery + age)
            if not age_feature or discovery + age - age_feature["observed_t"] > 2:
                continue
            f = age_feature
            future = peak_label(ticks, discovery + age, 60)
            if future["coverage"] != "bounded_observation":
                continue
            lossy = any(
                p["token_id"] == token_id
                and num(p["realized_pnl"]) is not None
                and float(p["realized_pnl"]) < 0
                for p in positions
            )
            group = (
                "bought_loser"
                if lossy
                else "missed_runner"
                if (token_id not in bought and future["peak_return_percent"] >= 25)
                else "other"
            )
            first_price = ticks[0]["price"]
            prior = asof(ticks, f["t"])
            cohort = {
                "mint": token["mint"],
                "token_age_seconds": age,
                "group": group,
                "quality": "MEDIUM",
                "forward_peak_60s_percent": future["peak_return_percent"],
                "return_since_first_observed_price_percent": (f["price"] / first_price - 1) * 100
                if f["price"] and first_price
                else None,
                "real_liquidity_sol": float(prior["real_quote_reserves"]) / 10**9
                if prior and prior["real_quote_reserves"] is not None
                else None,
                "market_cap_sol_assumed_1b_supply": f["price"] * 10**6 if f["price"] else None,
                "risk_score": f["risk"].get("risk_score"),
                "runner_score": None,
                "holder_growth": None,
                "profitable_wallet_participation": None,
                "bundled_supply_percent": None,
                **f["metrics"],
            }
            cohort.update(extension(ticks, discovery + age))
            # Risk is unavailable before assessed_at, even when linked to an earlier feature.
            if (
                not f["risk"].get("risk_assessed_at")
                or stamp(f["risk"]["risk_assessed_at"]) > discovery + age
            ):
                cohort["risk_score"] = None
            available_decision = asof(decisions.get(token_id, []), discovery + age)
            if available_decision:
                cohort["runner_score"] = num(available_decision["final_score"])
            cohorts.append(cohort)
    comparisons = []
    for age in (10, 20, 30, 60):
        age_rows = [r for r in cohorts if r["token_age_seconds"] == age]
        for field in (
            *METRICS,
            "real_liquidity_sol",
            "market_cap_sol_assumed_1b_supply",
            "risk_score",
            "runner_score",
            "return_since_first_observed_price_percent",
        ):
            a = [
                float(r[field])
                for r in age_rows
                if r["group"] == "bought_loser" and num(r.get(field)) is not None
            ]
            b = [
                float(r[field])
                for r in age_rows
                if r["group"] == "missed_runner" and num(r.get(field)) is not None
            ]
            pairs = [
                (float(r[field]), r["forward_peak_60s_percent"])
                for r in age_rows
                if num(r.get(field)) is not None
            ]
            comparisons.append(
                {
                    "age_seconds": age,
                    "feature": field,
                    "bought_losers": quantiles(a),
                    "missed_runners": quantiles(b),
                    "N_total": len(age_rows),
                    "N_usable": len(pairs),
                    "N_high_quality": 0,
                    "spearman_forward_peak": spearman(pairs),
                    **median_difference(a, b),
                }
            )
    concentration = []
    for portfolio in rows(source / "portfolios.jsonl"):
        sample = [p for p in positions if p["portfolio_id"] == portfolio["id"]]
        losses = sorted(
            [-float(p["realized_pnl"]) for p in sample if float(p["realized_pnl"]) < 0],
            reverse=True,
        )
        total = sum(losses)
        net = sum(float(p["realized_pnl"]) for p in sample)
        concentration.append(
            {
                "portfolio_id": portfolio["id"],
                "name": portfolio["name"],
                "N_total": len(sample),
                "N_losses": len(losses),
                "gross_loss_amount": total,
                "net_pnl": net,
                "top_1_fraction_of_gross_losses": sum(losses[:1]) / total if total else None,
                "top_3_fraction_of_gross_losses": sum(losses[:3]) / total if total else None,
                "top_5_fraction_of_gross_losses": sum(losses[:5]) / total if total else None,
                "tail_loss_amount_distribution": quantiles(losses),
                "net_pnl_if_top_loss_avoided_hindsight": net + sum(losses[:1]),
            }
        )
    rejected = Counter(
        reason for r in missed for reason in (r["first_decision_reasons"] or ["no_decision_record"])
    )
    summary = {
        "manifest": json.loads((source / "manifest.json").read_text()),
        "methodology": {
            "asof": "ingestion/availability timestamps, no interpolation or future risk",
            "runner_label": "observed peak >=25% in 10/30/60/120s or >=50% in 300s",
            "max_age_and_intertrade_gap_seconds": 2,
            "label_scope": "sparse observed marks; peak exit is hindsight and not net profit",
            "simulation": "conditional two-state round trip with 800ms delay, 50bps slippage, "
            "125bps venue, 50bps service each side, 0.00011 SOL network+priority each side",
            "jito_tip": "0 baseline: no live Jito path; separate stress scenario required",
            "real_reserves": "required; reject market changes, non-Pump.fun/WSOL, >300bps impact",
            "statistics": "one token per fixed age; 500 seeded token bootstrap replicates; "
            "descriptive, multiple testing and selection bias unresolved",
            "quality": "MEDIUM means bounded observed gaps, never verified complete chain coverage",
        },
        "N_total_observed_tokens": len(tokens),
        "N_trade_covered_tokens": len(trades),
        "N_discovered_tokens": json.loads((source / "manifest.json").read_text())[
            "total_discovered_tokens"
        ],
        "N_never_bought_trade_covered_tokens": sum(key not in bought for key in trades),
        "missed_runner_tokens": len(missed),
        "missed_runner_first_reasons": dict(rejected),
        "all_trades": perf(trade_report),
        "quality_counts": dict(Counter(r["quality"] for r in trade_report)),
        "mfe": quantiles(
            [
                r["observed_mfe_percent"]
                for r in trade_report
                if r["observed_mfe_percent"] is not None
            ]
        ),
        "mae": quantiles(
            [
                r["observed_mae_percent"]
                for r in trade_report
                if r["observed_mae_percent"] is not None
            ]
        ),
        "losers_with_positive_mark_mfe": sum(
            r["net_pnl"] < 0 and (r["observed_mfe_percent"] or 0) > 0 for r in trade_report
        ),
        "losers_with_recorded_positive_mfe": sum(
            r["net_pnl"] < 0 and (r["recorded_mfe_percent"] or 0) > 0 for r in trade_report
        ),
        "winners_with_observed_mae_below_minus10": sum(
            r["net_pnl"] > 0 and (r["observed_mae_percent"] or 0) < -10 for r in trade_report
        ),
        "entry_offsets": {
            str(o): perf([r for r in timing if r["offset_seconds"] == o]) for o in OFFSETS
        },
        "cost_sizes": {s: perf([r for r in costs if r["size_sol"] == s]) for s in SIZES},
        "observation_windows": {
            str(w): perf([r for r in observations if r["window_seconds"] == w]) for w in WINDOWS
        },
        "simulation_exclusions": dict(Counter(r.get("exclusion") for r in timing)),
        "worst_positions": [
            r
            for r in trade_report
            if r["portfolio_id"] == INCIDENT and r["position_id"] in {p["id"] for p in latest}
        ],
        "limitations": [
            "Not full counterfactual strategy execution; observed prices do not guarantee fills",
            "No high-quality complete chain histories; absent ticks are not proof of inactivity",
            "Repeated portfolio trades may share tokens; aggregate trade metrics are dependent",
            "Candidate-only follow-up, missing labels and future-peak conditioning bias groups",
            "Historical analysis is exploratory, not unseen validation; no parameters were changed",
        ],
    }
    summary["entry_offsets_common_panel"] = {
        "N_total": 225,
        "N_usable": len(
            set.intersection(
                *[
                    {
                        r["position_id"]
                        for r in timing
                        if r["offset_seconds"] == offset and r["net_return_percent"] is not None
                    }
                    for offset in OFFSETS
                ]
            )
        ),
        "N_high_quality": 0,
    }
    summary["preentry_signal_counts"] = {
        signal: {
            "losers": sum(r["net_pnl"] < 0 and signal in r["flags"] for r in preentry_flags),
            "winners": sum(r["net_pnl"] > 0 and signal in r["flags"] for r in preentry_flags),
            "N_feature_available": sum(r["feature_available_by_signal"] for r in preentry_flags),
        }
        for signal in (
            "large_sell_with_price_shock",
            "buyer_deceleration_and_net_selling",
            "reserves_and_price_falling",
        )
    }
    summary["extension_buckets"] = {}
    for lo, hi in ((-10000, 0), (0, 20), (20, 40), (40, 60), (60, 100), (100, 1000000)):
        selected = [
            r
            for r in trade_report
            if r["return_first_observed_price_to_entry_mark_percent"] is not None
            and lo <= r["return_first_observed_price_to_entry_mark_percent"] < hi
        ]
        summary["extension_buckets"][f"{lo}_to_{hi}"] = perf(selected)
    # Tip stress rows must not silently duplicate the baseline size panel.
    summary["cost_sizes"] = {
        s: perf([r for r in costs if r["size_sol"] == s and not r.get("scenario")]) for s in SIZES
    }
    summary["tip_stress"] = perf([r for r in costs if r.get("scenario")])
    for name, data in (
        ("trade_excursions", trade_report),
        ("entry_offsets", timing),
        ("cost_sizes", costs),
        ("exit_signals", exit_report),
        ("worst_trade_timeline", sorted(timeline, key=lambda r: r["t"])),
        ("candidate_labels", labels),
        ("missed_runners", missed),
        ("age_matched_features", cohorts),
        ("feature_comparisons", comparisons),
        ("observation_windows", observations),
        ("loss_concentration", concentration),
        ("preentry_signals", preentry_flags),
    ):
        write_csv(output / f"{name}.csv", data)
        write_json(output / f"{name}.json", data)
    write_json(output / "summary.json", summary)
    write_json(output / "source_manifest.json", summary["manifest"])
    write_json(
        output / "research_code.json",
        {"sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify_capture(args.source)
    result = analyze(args.source, args.output)
    print(
        json.dumps(
            {
                "positions": result["all_trades"],
                "missed_runners": result["missed_runner_tokens"],
                "quality": result["quality_counts"],
            },
            default=str,
        )
    )


if __name__ == "__main__":
    main()
