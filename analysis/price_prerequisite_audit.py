"""Read-only, bounded analysis of captured price evidence. No worker or provider calls."""

import csv
import hashlib
import itertools
import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "research_sessions/strategy-2026-10-01"
CAPP = "H1qib6bJJ2EUA61nwq8XuFfEZDq51HW9XKKey57Tpump"
manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
verified_inputs = {}
for name in ("positions", "trade_outcomes", "orders", "market_trades"):
    with (RAW / f"{name}.jsonl").open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if digest != manifest[name]["sha256"]:
        raise ValueError(f"capture hash mismatch: {name}")
    verified_inputs[name] = digest


def rows(name):
    with (RAW / f"{name}.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


positions = list(rows("positions"))
outcomes = {r["position_id"]: r for r in rows("trade_outcomes")}
token_ids = {r["token_id"] for r in positions}
trades = defaultdict(list)
for trade in rows("market_trades"):
    if trade["token_id"] in token_ids:
        trade["receipt"] = stamp(trade["provider_received_at"] or trade["ingested_at"])
        trades[trade["token_id"]].append(trade)
results = []
for p in positions:
    opened = stamp(p["opened_at"])
    closed = stamp(p["closed_at"]) if p["closed_at"] else None
    sample = sorted([
        r for r in trades[p["token_id"]]
        if closed and opened <= r["receipt"] <= closed
        and r["market_address"] == p["market_address"]
    ], key=lambda r: r["receipt"])
    bounds = [opened, *[r["receipt"] for r in sample], closed] if closed else []
    gap = max((b-a for a, b in itertools.pairwise(bounds)), default=None)
    o = outcomes.get(p["id"], {})
    result = {
        "position_id": p["id"], "portfolio_id": p["portfolio_id"], "mint": p["mint"],
        "status": p["status"], "tick_count": len(sample),
        "max_receipt_silence_seconds": gap,
        "coverage": "observed" if sample else "no_ticks_entire_holding_interval",
        "net_pnl": float(p["realized_pnl"]),
        "net_return_percent": float(o["pnl_percent"])
        if o.get("pnl_percent") is not None else None,
    }
    results.append(result)
    if p["mint"] == CAPP:
        last = sample[-1]
        longest = max(itertools.pairwise(bounds), key=lambda pair: pair[1]-pair[0])
        orders = [r for r in rows("orders") if r["token_id"] == p["token_id"]
                  and r["portfolio_id"] == p["portfolio_id"] and r["status"] == "filled"]
        capp = {
            "position": p,
            "outcome": {k: v for k, v in o.items() if not k.endswith("snapshot_json")},
            "filled_orders": orders,
            "last_received_tick": last,
            "last_tick_age_at_close_seconds": closed-last["receipt"],
            "longest_receipt_silence_seconds": longest[1]-longest[0],
            "longest_gap_start": datetime.fromtimestamp(longest[0], UTC).isoformat(),
            "longest_gap_end": datetime.fromtimestamp(longest[1], UTC).isoformat(),
            "near_exit_ticks": [r for r in trades[p["token_id"]]
                                if closed-3 <= r["receipt"] <= closed+3],
        }


def stats(group):
    returns = [r["net_return_percent"] for r in group if r["net_return_percent"] is not None]
    return {
        "positions": len(group), "positions_with_return": len(returns),
        "wins": sum(r["net_pnl"] > 0 for r in group),
        "losses": sum(r["net_pnl"] < 0 for r in group),
        "pooled_pnl_currency_units": sum(r["net_pnl"] for r in group),
        "median_return_percent": statistics.median(returns) if returns else None,
        "mean_return_percent": statistics.mean(returns) if returns else None,
        "loss_below_minus_30_percent_count": sum(r < -30 for r in returns),
    }


summary = {
    "source_snapshot_utc": manifest["database_time_utc"],
    "verified_input_sha256": verified_inputs,
    "method": "receipt timestamps; same market; entry/exit boundaries included; strict > thresholds",
    "interpretation": "Silence may be no trades, lost subscriptions, outage or collection gaps. Not causal.",
    "capital_caveat": "Pooled USD/USDT recorded PnL mixes portfolios, capital and dates; not strategy EV.",
    "positions": len(results), "no_in_position_ticks": sum(r["tick_count"] == 0 for r in results),
    "thresholds": {},
}
for limit in (1, 5, 10, 30, 60):
    above = [r for r in results if r["max_receipt_silence_seconds"] is not None
             and r["max_receipt_silence_seconds"] > limit]
    below = [r for r in results if r["max_receipt_silence_seconds"] is not None
             and r["max_receipt_silence_seconds"] <= limit]
    summary["thresholds"][str(limit)] = {"above": stats(above), "at_or_below": stats(below)}
    summary["thresholds"][str(limit)]["by_portfolio_above"] = {
        pid: stats([r for r in above if r["portfolio_id"] == pid])
        for pid in sorted({r["portfolio_id"] for r in above})
    }
(ROOT / "analysis/feed_gap_analysis.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
(ROOT / "analysis/cappuccinu_price_evidence.json").write_text(json.dumps(capp, indent=2), encoding="utf-8")
with (ROOT / "analysis/feed_gap_positions.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)
print(json.dumps({"gaps": {k: {side: v[side] for side in ("above", "at_or_below")}
                           for k, v in summary["thresholds"].items()},
                  "capp_last_age": capp["last_tick_age_at_close_seconds"],
                  "capp_gap_start": capp["longest_gap_start"],
                  "capp_gap_end": capp["longest_gap_end"]}, indent=2))
