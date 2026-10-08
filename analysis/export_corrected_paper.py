"""Read-only export of the actual corrected cohort; missing measurements stay null."""
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal as D
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, inspect, select, text

from memebot.core.config import Settings
from memebot.core.metrics import distribution
from memebot.paper.migration_exit import migration_sell_quote
from memebot.paper.standard_math import sell_quote
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.models import (
    DecisionOutcomeRecord, DomainEventRecord, PaperOrderRecord, PaperPortfolioRecord,
    PaperPositionRecord, ProviderHealthRecord, TokenRecord, TradingControlRecord,
)

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"


def write(name, value):
    (ANALYSIS / name).write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def row(value):
    return {c.key: getattr(value, c.key) for c in inspect(type(value)).columns}


def ev(fill):
    return {e["code"]: e["value"] for e in fill["evidence"]}


def decompose(fills):
    entry = next(f for f in fills if f["side"] == "buy")
    sells = [f for f in fills if f["side"] == "sell"]
    e = ev(entry)
    q0, qa = D(e["unadjusted_token_amount_raw"]), D(entry["token_amount_raw"])
    unit = D(entry["quote_price_in_portfolio_currency"]) / 10**9
    curve_cost = (D(entry["gross_quote_amount_raw"]) - D(entry["venue_fee_quote_raw"])) * unit
    entry_cost = D(entry["gross_portfolio_amount"]) + (
        D(entry["network_fee_quote_raw"]) + D(entry["execution_provider_fee_quote_raw"])
    ) * unit
    curve_exit = actual_gross = proceeds = D(0)
    for fill in sells:
        state = fill["execution_state"]
        quantity = int(q0 * D(fill["token_amount_raw"]) / qa)
        quoted = migration_sell_quote(state, quantity) if state.get("model") == "canonical_pumpswap_exit" else sell_quote(state["curve"], quantity, state["rates"])
        curve_exit += D(quoted["gross_output"]) * D(fill["quote_price_in_portfolio_currency"]) / 10**9
        actual_gross += D(fill["gross_portfolio_amount"])
        proceeds += D(fill["gross_portfolio_amount"]) - D(fill["total_fee_portfolio"])
    fees = sum((D(f["total_fee_portfolio"]) for f in fills), D(0))
    return {"curve_price_pnl_before_fees_friction": curve_exit - curve_cost,
            "friction_cost": curve_exit - actual_gross, "fees": fees,
            "ledger_net_pnl": proceeds - entry_cost,
            "basis": "saved exit banks, undo configured buy/sell friction; same timing, no own-trade reserve overlay"}


def runtime_metrics():
    values = []
    path = ANALYSIS / "paper_corrected_alchemy.err.log"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                value = json.loads(line)
                if value.get("event") == "runtime_metrics":
                    values.append(value)
            except ValueError:
                pass
    return values[-1] if values else {}


async def main():
    run = json.loads((ANALYSIS / "paper_corrected_run_state.json").read_text(encoding="utf-8"))
    pid = UUID(run["portfolio_id"])
    start = datetime.fromisoformat(run["started_at"])
    end = datetime.fromisoformat(run.get("ended_at") or datetime.now(UTC).isoformat())
    database = Database(create_database_engine(Settings().database_url))
    try:
        async with database.sessions() as session, session.begin():
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            positions = list(await session.scalars(select(PaperPositionRecord).where(PaperPositionRecord.portfolio_id == pid)))
            orders = list(await session.scalars(select(PaperOrderRecord).where(PaperOrderRecord.portfolio_id == pid).order_by(PaperOrderRecord.created_at)))
            decisions = list(await session.scalars(select(DecisionOutcomeRecord).where(
                DecisionOutcomeRecord.active_strategy.is_(True), DecisionOutcomeRecord.decided_at >= start,
                DecisionOutcomeRecord.decided_at <= end)))
            portfolio = await session.get(PaperPortfolioRecord, pid)
            control = await session.get(TradingControlRecord, 1)
            health = list(await session.scalars(select(ProviderHealthRecord)))
            event_counts = dict((await session.execute(select(DomainEventRecord.event_type, func.count())
                .where(DomainEventRecord.provider == "solana_rpc_pump", DomainEventRecord.ingested_at >= start,
                       DomainEventRecord.ingested_at <= end).group_by(DomainEventRecord.event_type))).all())
            # Decision evidence only; do not export huge global discovery payloads.
            ids = [d.decision_event_id for d in decisions]
            raw = {r.event_id: r.payload for r in await session.scalars(select(DomainEventRecord).where(DomainEventRecord.event_id.in_(ids)))} if ids else {}
            tokens = {r.id: r for r in await session.scalars(select(TokenRecord).where(TokenRecord.id.in_([p.token_id for p in positions])))} if positions else {}
        trades, paths, shadows, mfe_samples, mae_samples = [], [], [], [], []
        entry_hurdles, traces, decompositions = [], [], []
        filled = [o for o in orders if o.fill_json]
        for p in sorted(positions, key=lambda p: p.opened_at):
            linked = [o for o in filled if o.mint == p.mint and o.filled_at >= p.opened_at and (p.closed_at is None or o.filled_at <= p.closed_at)]
            bank_path = (p.execution_mark_json or {}).get("exit_evidence", {})
            bank = next((o.fill_json for o in linked if o.side == "buy"), {})
            evidence = ev(bank) if bank else {}
            if evidence.get("estimated_round_trip_cost_bps") is not None:
                entry_hurdles.append(float(D(evidence["estimated_round_trip_cost_bps"]) / 100))
            basis = D(bank.get("gross_portfolio_amount", 0)) + (
                D(bank.get("network_fee_quote_raw", 0)) + D(bank.get("execution_provider_fee_quote_raw", 0))
            ) * D(bank.get("quote_price_in_portfolio_currency", 0)) / 10**9
            # Quantity, rather than equal timestamps, identifies which actual partials
            # precede a mark. The final detection mark is retained before its own sell.
            entry_quantity = D(bank.get("token_amount_raw", 0))
            full_returns = []
            for mark in bank_path.get("marks", []):
                sold_before = entry_quantity - D(mark["quantity"])
                seen_quantity = prior_realized = D(0)
                for order in linked:
                    if order.side != "sell":
                        continue
                    fill = order.fill_json
                    q = D(fill["token_amount_raw"])
                    if seen_quantity + q > sold_before:
                        break
                    prior_realized += D(fill["gross_portfolio_amount"]) - D(fill["total_fee_portfolio"]) - basis * q / entry_quantity
                    seen_quantity += q
                total_return = (prior_realized + D(mark["net_pnl"])) / basis * 100
                mark["actual_realized_pnl_before_mark"] = str(prior_realized)
                mark["whole_entry_net_return_percent"] = str(total_return)
                full_returns.append(total_return)
            sampled_path = {
                "mfe_net_percent": max(full_returns) if full_returns else None,
                "mae_net_percent": min(full_returns) if full_returns else None,
                "profit_surrendered_percentage_points": max(full_returns) - p.realized_pnl / basis * 100 if full_returns and p.status == "closed" else None,
                "scope": "sampled retained executable marks; actual prior partial proceeds / original actual entry basis",
                "truncated": bool(bank_path.get("dropped_mark_count", 0)),
            }
            if full_returns:
                mfe_samples.append(float(max(full_returns)))
                mae_samples.append(float(min(full_returns)))
            decomposition = decompose([{**o.fill_json, "side": o.side} for o in linked]) if p.status == "closed" else None
            if decomposition:
                assert abs(decomposition["ledger_net_pnl"] - p.realized_pnl) < D("0.0000001")
                decompositions.append(decomposition)
            token = tokens[p.token_id]
            trade = {**row(p), "name": token.name, "symbol": token.symbol, "entry_cost_basis": basis,
                     "decision_price": bank.get("decision_price"), "orders": [row(o) for o in linked],
                     "execution_decomposition": decomposition, "sampled_executable_path": sampled_path}
            trades.append(trade)
            paths.append({"position_id": str(p.id), "mint": p.mint, **bank_path})
            shadows.append({"position_id": str(p.id), "mint": p.mint,
                            "path_total_marks": bank_path.get("total_mark_count", 0),
                            "path_dropped_marks": bank_path.get("dropped_mark_count", 0),
                            "policies": bank_path.get("shadow_policies", {})})
        for o in filled:
            if o.side == "sell":
                traces.append({"position_mint": o.mint, "order_event_id": str(o.event_id),
                               "exit_reason": o.exit_reason, **o.fill_json.get("exit_telemetry", {}),
                               "execution_diagnostics": o.fill_json.get("execution_diagnostics", {})})
        candidates = []
        missing, quality, completeness, state_reasons = Counter(), Counter(), Counter(), Counter()
        null_rejections = 0
        for d in decisions:
            payload = raw.get(d.decision_event_id, {})
            score = payload.get("score", {})
            reasons = d.decision_reasons
            reject = any(reason in {"UNKNOWN_REQUIRED_PRICE_CHANGE", "REQUIRED_PRICE_SIGNAL_INCOMPLETE"} for reason in reasons)
            null_rejections += reject
            quality[(payload.get("price_evidence") or {}).get("observational_trust", "MISSING")] += 1
            price_evidence = payload.get("price_evidence") or {}
            state_reasons[price_evidence.get("invalidation_reason") or price_evidence.get("state_reason") or "NO_STATE_REASON"] += 1
            momentum = next((c for c in score.get("components", []) if c["name"] == "momentum"), {})
            completeness[momentum.get("component_status", "LEGACY_UNKNOWN")] += 1
            missing.update(score.get("missing_required_inputs", []))
            candidates.append({"mint": d.mint, "decided_at": d.decided_at, "action": d.action,
                               "decision_price": payload.get("decision_price"), "price_evidence": payload.get("price_evidence"),
                               "score": score, "reasons": reasons})
        closed = sorted([p for p in positions if p.status == "closed"], key=lambda p: p.closed_at)
        pnls = [p.realized_pnl for p in closed]
        wins, losses = [v for v in pnls if v > 0], [v for v in pnls if v < 0]
        net = sum(pnls, D(0))
        equity = peak = portfolio.initial_cash
        drawdown = D(0)
        for pnl in pnls:
            equity += pnl
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        fees = sum((D(o.fill_json["total_fee_portfolio"]) for o in filled), D(0))
        latency_keys = ["queue_wait_ms", "lock_wait_ms", "RPC_ms", "simulated_execution_delay_ms", "trigger_to_fill_ms"]
        latencies = {key: distribution([float(t[key]) for t in traces if t.get(key) is not None]) for key in latency_keys}
        stop_detection = []
        for trace in traces:
            if trace.get("event_received_at") and trace.get("exit_triggered_at"):
                delay = (datetime.fromisoformat(trace["exit_triggered_at"]) - datetime.fromisoformat(trace["event_received_at"])).total_seconds() * 1000
                stop_detection.append(delay)
        latencies["event_received_to_trigger_ms"] = distribution(stop_detection)
        stop_traces = [t for t in traces if t["exit_reason"] == "stop_loss"]
        latencies["stop_trigger_to_fill_ms"] = distribution(
            [float(t["trigger_to_fill_ms"]) for t in stop_traces if t.get("trigger_to_fill_ms") is not None]
        )
        latencies["stop_event_received_to_trigger_ms"] = distribution([
            (datetime.fromisoformat(t["exit_triggered_at"]) - datetime.fromisoformat(t["event_received_at"])).total_seconds() * 1000
            for t in stop_traces if t.get("event_received_at") and t.get("exit_triggered_at")
        ])
        overshoot = []
        for trace in stop_traces:
            diagnostic = trace["execution_diagnostics"]
            if diagnostic.get("net_executable_pnl_percent") is not None:
                threshold = D(diagnostic["shadow_policies"]["CURRENT_POLICY"]["stop_percent"])
                value = max(D(0), -D(diagnostic["net_executable_pnl_percent"]) - threshold)
                trace["net_stop_overshoot_percentage_points"] = str(value)
                overshoot.append(float(value))
        latencies["stop_overshoot_percentage_points"] = distribution(overshoot)
        sample = {"candidates_observed": len({d.mint for d in decisions}), "decision_evaluations": len(decisions),
                  "candidate_definition": "unique markets receiving an active-strategy decision after existing prefilter/risk assessment",
                  "rejected_missing_price_signal": null_rejections, "rejection_unit": "decision evaluations, reasons may overlap",
                  "unique_markets_rejected_missing_price_signal": len({c["mint"] for c in candidates if any(r in {"UNKNOWN_REQUIRED_PRICE_CHANGE", "REQUIRED_PRICE_SIGNAL_INCOMPLETE"} for r in c["reasons"])}),
                  "qualified_entries": sum(d.action == "enter_candidate" for d in decisions),
                  "filled_entries": sum(o.side == "buy" for o in filled), "completed_trades": len(closed),
                  "open_positions": len(positions) - len(closed), "native_event_counts": event_counts,
                  "wins": len(wins), "losses": len(losses)}
        perf = {"gross_pnl_before_fees": net + sum((d["fees"] for d in decompositions), D(0)),
                "curve_price_pnl_before_fees_friction": sum((d["curve_price_pnl_before_fees_friction"] for d in decompositions), D(0)),
                "execution_friction": sum((d["friction_cost"] for d in decompositions), D(0)),
                "net_pnl": net, "fees_all_fills": fees, "currency": portfolio.currency,
                "win_rate_percent": D(100) * len(wins) / len(closed) if closed else None,
                "average_win": sum(wins, D(0)) / len(wins) if wins else None,
                "average_loss": sum(losses, D(0)) / len(losses) if losses else None,
                "profit_factor": sum(wins, D(0)) / abs(sum(losses, D(0))) if losses else None,
                "expectancy": net / len(closed) if closed else None, "max_realized_drawdown": drawdown if closed else None,
                "drawdown_scope": "closed-trade equity; asynchronous open-position marks do not establish synchronized account equity",
                "positive_expectancy_evidence": "INSUFFICIENT_DATA" if len(closed) < 50 else "Requires prospective statistical assessment",
                "entry_round_trip_hurdle_percent": distribution(entry_hurdles)}
        perf["sampled_executable_mfe_mae"] = {
            "mfe_net_percent": distribution(mfe_samples), "mae_net_percent": distribution(mae_samples),
            "positions_with_marks": len(mfe_samples), "positions_without_marks": len(positions) - len(mfe_samples),
            "coverage": "sampled retained path; truncated history flagged per position, not continuous market extrema",
        }
        old = json.loads((ANALYSIS / "loss_audit_20261003/findings.json").read_text(encoding="utf-8"))
        metrics = runtime_metrics()
        summary = {"run": run, "exported_at": datetime.now(UTC), "sample": sample, "performance": perf,
                   "entry_signal_quality": dict(quality), "momentum_component_status": dict(completeness),
                   "missing_required_inputs": dict(missing), "portfolio": row(portfolio),
                   "historical_state_reasons": dict(state_reasons),
                   "trading_control": row(control), "latencies_ms": latencies, "runtime_metrics_last_snapshot": metrics,
                   "provider_health": [row(h) for h in health], "old_cohorts": [c["summary"] for c in old["cohorts"]],
                   "baseline_comparability": "Old null-price entries were invalid historical signals; provider endpoint also changed due Helius HTTP429. No causal or significance claim."}
        write("paper_corrected_trades.json", {"run": run, "trades": trades, "orders": [row(o) for o in orders], "candidates": candidates, "executable_paths": paths})
        write("paper_exit_latency.json", {"run": run, "units": "ms", "orders": traces, "distributions": latencies,
              "old_stop_detection_and_trigger_latency": None, "old_unavailable_reason": "No comparable receipt/trigger trace in historical fills"})
        shadow_summary = {}
        for name in ("CURRENT_POLICY", "EARLIER_PROFIT_PROTECTION", "DEFENSIVE_PROFIT_PROTECTION"):
            policies = [p["policies"][name] for p in shadows if name in p["policies"]]
            endings = [p for p in policies if p.get("closed_at")]
            shadow_summary[name] = {
                "positions_observed": len(policies), "closed_counterfactuals": len(endings),
                "censored_open_counterfactuals": len(policies) - len(endings),
                "net_return_percent": distribution([float(p["net_return_percent"]) for p in endings]),
                "profit_surrendered_percentage_points": distribution([float(p["profit_surrendered_percentage_points"]) for p in endings]),
            }
        write("paper_shadow_exits.json", {"run": run, "positions": shadows, "summary": shadow_summary, "winner_selected": False,
              "scope": "same entry and retained executable marks until primary close; mark fills exclude future execution delay, open shadow endings censored"})
        write("paper_corrected_performance.json", summary)
        print(json.dumps({"status": run["status"], **sample, "entry_signal_quality": dict(quality), "missing_required_inputs": dict(missing), "net_pnl": str(net)}))
    finally:
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
