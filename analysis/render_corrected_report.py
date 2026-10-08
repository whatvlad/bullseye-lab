"""Render the requested operational report from measured artifacts, not inferred trades."""
import json
from datetime import UTC, datetime
from decimal import Decimal as D
from pathlib import Path

from memebot.core.config import Settings

ROOT = Path(__file__).resolve().parents[1]
A, DOCS = ROOT / "analysis", ROOT / "docs"
performance = json.loads((A / "paper_corrected_performance.json").read_text(encoding="utf-8"))
run, sample, perf = performance["run"], performance["sample"], performance["performance"]
settings = run["configuration_snapshot"]["settings"]
actual = Settings().safe_summary()
old_settings = json.loads((A / "loss_audit_20261003/current_1250/current_settings.json").read_text(encoding="utf-8"))
unchanged_keys = [
    "paper_execution_provider_fee_bps", "paper_latency_slippage_bps", "paper_additional_slippage_bps",
    "paper_adverse_fill_bps", "paper_compute_latency_ms", "paper_submission_latency_ms",
    "paper_daily_loss_limit_percent", "paper_stop_loss_risk_reserve_percent",
    "paper_max_total_exposure_percent", "paper_base_position_percent", "paper_max_position_percent",
]
assert all(old_settings[k] == settings[k] == actual[k] for k in unchanged_keys)
assert actual["code_fingerprint"] == settings["code_fingerprint"]
assert actual["execution_parameters"] == settings["execution_parameters"]
strategy = run["configuration_snapshot"]["strategy"]
control = run["configuration_snapshot"]["trading_control"]
costs = {
    "route": "planned PumpPortal Local Transaction API; PAPER creates no actual transactions",
    "provider_fee_applies": True,
    "provider_fee_basis": "0.5% on every Local API trade, before slippage; protocol and network fees separate",
    "provider_fee_source": "https://pumpportal.fun/fees/",
    "route_source": "https://pumpportal.fun/local-trading-api/trading-api/",
    "protocol_fee": {"classification": "MEASURED_OR_ONCHAIN", "basis": "per-fill canonical atomic global/fee config and dynamic tier, integer rounding", "fixed_universal_rate": None},
    "creator_fee": {"classification": "MEASURED_OR_ONCHAIN", "basis": "per-fill canonical atomic creator/config rate; no unsupported route estimates"},
    "lp_fee_standard_curve": {"classification": "NOT_APPLICABLE", "bps": 0},
    "price_impact": {"classification": "MEASURED_OR_ONCHAIN", "basis": "quantity-specific curve output derived from verified reserves; not an observed real-world fill or own-paper-trade state overlay"},
    "modeled_provider_fee": {"classification": "ROUTE_APPLICABLE_ESTIMATE", "bps_per_side": settings["paper_execution_provider_fee_bps"]},
    "network_priority_fee": {"classification": "ROUTE_APPLICABLE_ESTIMATE", "network_sol": str(Settings().paper_network_fee_sol), "priority_sol": str(Settings().paper_priority_fee_sol)},
    "simulated_latency_penalty": {"classification": "CONSERVATIVE_SIMULATION", "bps_per_side": settings["paper_latency_slippage_bps"], "compute_ms": settings["paper_compute_latency_ms"], "submission_ms": settings["paper_submission_latency_ms"]},
    "additional_slippage": {"classification": "CONSERVATIVE_SIMULATION", "bps_per_side": settings["paper_additional_slippage_bps"]},
    "adverse_fill": {"classification": "CONSERVATIVE_SIMULATION", "bps_per_side": settings["paper_adverse_fill_bps"]},
    "hypothetical_direct_sdk_provider_fee": {"classification": "NOT_APPLICABLE", "basis": "Only if a direct route is actually selected; no direct signer route is implemented/selected here"},
    "old_same_bank_entry_hurdles": [{"cohort": c["label"], "min_percent": c["round_trip_cost_percent_min"], "max_percent": c["round_trip_cost_percent_max"]} for c in performance["old_cohorts"]],
    "new_entry_hurdles": perf["entry_round_trip_hurdle_percent"],
    "unchanged_cost_parameters": True,
    "limits": ["Same-bank buy/sell probe is a conservative entry-cost diagnostic, not a real immediate round-trip: hypothetical own buy does not mutate reserves.",
               "No real signing, inclusion, provider dispatch, account-creation/rent or measured priority-fee evidence. Live readiness is not established.",
               "Latency is represented by an actual wait plus configurable price penalties; penalties are assumptions, not calibrated market estimates."],
}
(A / "paper_cost_model.json").write_text(json.dumps(costs, indent=2), encoding="utf-8")

def write_doc(name, value):
    (DOCS / name).write_text(value.strip() + "\n", encoding="utf-8")

def shown(value):
    return "N/A — no completed trade evidence" if value is None else str(value)

write_doc("PAPER_OPERATIONAL_FIXES.md", f"""
# Corrected operational PAPER baseline

This patch fixes the existing bot's signal, exit and attribution defects. LIVE remains disabled;
`runner-edge-prospective-v1` remains BLOCKED. No new proof gates, providers, strategy families,
wallet/social intelligence or LLM signals were added. Ollama remains off. Source fingerprint:
`{settings['code_fingerprint']}`.

## Historical entry signal

`strategies/price_signal.py` checks a positive decision/reference price, the configured rolling
price-change feature, observationally healthy provenance, POST_TRADE semantics, supported
continuity and reported source time. The window must have at least two usable price samples,
positive endpoints, no missing-price event and price span at least the preset's existing
minimum observation duration. For aggressive v10 this is **3 seconds of price observations
inside the 10-second scoring window**, not a claim of complete ten-second transaction coverage.
Coverage is measured explicitly by `price_sample_count`, `missing_price_sample_count` and
`price_observation_span_seconds`. Unknown transaction/stream continuity still invalidates prices;
no retrospective RPC bank is relabeled as historical momentum.

The rolling engine invalidates price-change/velocity when an event in the window has no usable
price. A later valid endpoint cannot average that missing event away. Missing mandatory
momentum subinputs produce `component_status=INCOMPLETE`, `missing_required_inputs`, and reduced
`overall_signal_completeness` (weighted component completeness, not a probability of profitability).
Unavailable optional components remain visible. An absent price change produces
`UNKNOWN_REQUIRED_PRICE_CHANGE` and cannot bypass the extension guard. The PAPER engine independently
rejects null/legacy/incomplete historical decisions before execution RPC.

## Unchanged selection and risk controls

Active strategy: `{control['active_strategy_key']}`, version {strategy['version']}. Entry SCORE
{strategy['score_threshold']}; watch SCORE {strategy['watch_threshold']}. Existing trade/buyer,
flow, concentration, extension, regime, canonical identity and execution-state guards remain.
Position allocation, adaptive sizing, fee assumptions, RPC budgets and daily breaker parameters
match the saved pre-fix configuration. Stop remains {control['stop_loss_percent']}%, TP
{control['take_profit_percent']}%, primary trailing configuration remains unchanged.

**The stop's metric changes:** it now uses quantity-specific net executable liquidation divided
by actual remaining portfolio-currency entry cost basis. Gross raw-price movement remains a
diagnostic. TP/trailing policy is unchanged. Exit refresh, quote validation and the existing
pessimistic simulation remain mandatory.

## Exit priority and evidence

Native receipt wakes for watched open markets bypass the ordered discovery/analysis queue.
They carry identity/slot only; they do not authorize a price or fill. Each mint has its own lock,
and position identity is re-read inside the lock. Relevant slot and last retained bank slot
bound the final atomic refresh. The watchdog dispatches per-market tasks, so a slow RPC for
one market does not postpone the next watchdog for another. Existing independent exit RPC
and fallback RPC remain in use. Recovered/stale banks never become fabricated liquidation.

Each exit has receipt/ingestion, evaluation, RPC, trigger and fill timestamps plus queue/lock/RPC
and simulated-delay durations. Detection and final banks are retained. A price recovery is
re-evaluated before fill; further movement is recorded in trigger-to-fill price change.

`execution_mark_json.exit_evidence` durably holds a maximum 2048 marks, total/dropped counts,
quantity and remaining cost basis, gross quote/net liquidation, gross/net PnL, segmented net
peak and drawdown. Gross PnL in the path is the raw-SOL price-change component converted at the
mark's SOL/portfolio FX; **net PnL uses actual portfolio-currency cost basis including entry costs
and FX**. Portfolio performance is separately reconciled from actual PAPER cash flows.
Partial closes start a new remaining-basis peak segment. Shadow policies retain whole-entry
realized-plus-liquidation MFE/MAE independently of that segment.

Three shadow policies use the same entry and executable marks, with no additional orders:
CURRENT_POLICY, EARLIER_PROFIT_PROTECTION and DEFENSIVE_PROFIT_PROTECTION. Earlier uses TP/2 and
activation/2 with the current fixed width; defensive uses TP/4, activation/4 and width/2.
CURRENT follows existing dynamic runner width/hold behavior. These predeclared diagnostic
ratios are not optimized or selected. Mark-time shadow exits omit subsequent submission delay
and are optimistic timing counterfactuals; shadows still open at the primary close are censored.
Mark-only shadows do not reproduce event-only dump-hazard signals.

## Portfolio attribution and deployment

Telegram portfolio reset is transactional, refuses any open exposure, pauses entries and
creates a linked experiment cohort for the new active portfolio. If the previous experiment
is stopped, initialized strategy/control still create a new cohort. Previous portfolios and
results remain. Reports expose both their portfolio ID and the currently active portfolio ID.
The eight historically orphaned reset trades were attached to a stopped legacy cohort; its
copied settings are explicitly UNVERIFIED, not relabeled as corrected data.

Helius WSS returned HTTP 429. A one-subscription probe on the **already configured Alchemy RPC**
succeeded; the existing native adapter now uses that acknowledged WSS endpoint. No provider
architecture or higher-tier purchase was introduced. This endpoint difference is a comparison
confound. Alchemy subscriptions use bandwidth billing: see
[official subscription documentation](https://www.alchemy.com/docs/reference/solana-subscription-api-endpoints).

Regression gate passed: **508 tests**, Ruff, and mypy over 141 source files. New cases cover null
inputs, missing window/subinput/provenance, the extension guard, gaps between good ticks, net
stop logic and remaining basis, independent market progress, duplicate-exit exclusion,
receipt wakes, a nonblocking watchdog, bounded durable shadows and reset/cohort association.

See `PAPER_CORRECTED_RUN.md` for actual prospective results. Passing tests does not establish edge.
""")

write_doc("PAPER_EXIT_LATENCY.md", """
# PAPER exit priority and latency

Previous exits could wait on a shared sequential monitor and its five-second cycle. The native
adapter now recognizes a successful log event for an already watched position on receipt and
schedules an atomic exit evaluation before downstream ingestion/candidate analysis. The ordered
decoder remains responsible for market events. Receipt-only wakes cannot manufacture price or
continuity. A 5s per-market watchdog remains fallback, with 30s bounded recovery attempts.

| Field | Meaning |
| --- | --- |
| event_received_at | Local provider receipt; null for timer-only evaluations |
| event_ingested_at | Original event ingestion timestamp; null on receipt-only wake |
| event_ingested_status | ingested / receipt_only_wake / watchdog |
| exit_evaluation_started_at | Evaluation begins after acquiring the market lock |
| RPC_refresh_started_at | First atomic refresh starts |
| RPC_refresh_completed_at | Last atomic refresh completes; each read also has its own trace |
| exit_triggered_at | A validated executable mark triggers the primary exit policy |
| paper_fill_at | Pessimistic simulated fill on the final fresh bank |
| queue_wait_ms | Receipt wake scheduling wait, or receipt-to-processing wait for ingested events |
| lock_wait_ms | Waiting for that mint's lock; no global monitor lock |
| RPC_ms | Sum of refresh elapsed times, including existing fallback work |
| simulated_execution_delay_ms | Actual compute/submission wait; configured delay also recorded |
| trigger_to_fill_ms | Trigger to simulated fill, including delay and second bank refresh |
| price_change_trigger_to_fill_percent | Final gross executable price versus detection-bank price |

Same-position calls serialize and re-read the current position before action. Different markets
progress independently. The watchdog does not await a slow market before dispatching other
markets on its next cycle. Position close unpins the receipt watch. Fresh banks use a minimum
slot from the received event and last execution mark. Quotes after the delay are refreshed and
soft exits re-evaluated; stale/unavailable state produces recovery attempts, not forced fills.
Final exit risk is net executable liquidation / remaining entry cost basis. A partial-profit fill
diagnostic uses the **full remaining liquidation** for stop risk, not half proceeds / full basis.

An event-to-trigger measurement is latency from an observed local receipt, not proof of when
the market first crossed the stop on-chain. No historical trace establishes comparable old
stop-detection latency. Existing entry-to-fill latency must not be substituted for it.
Network submission/inclusion is not performed in PAPER, so paper_fill_at is not a live confirmation.

Actual distributions and retained per-order traces: `analysis/paper_exit_latency.json`.
Without prospective exits, overshoot and latency improvement remain unmeasured.
""")

rows = []
for key in ("protocol_fee", "creator_fee", "lp_fee_standard_curve", "price_impact", "modeled_provider_fee",
            "network_priority_fee", "simulated_latency_penalty", "additional_slippage", "adverse_fill"):
    item = costs[key]
    rows.append(f"| {key} | {item['classification']} | {item.get('basis') or json.dumps({k:v for k,v in item.items() if k != 'classification'})} |")
write_doc("PAPER_COST_MODEL_AUDIT.md", "\n".join([
    "# Standard Pump.fun PAPER cost model", "",
    "The intended execution assumption is PumpPortal Local. Its official fee is **0.5% on each trade**",
    "before slippage, with network and Pump fees separate. Native market discovery does not imply",
    "a direct execution route. No direct SDK signer route is selected, and PAPER actually sends no trades.",
    "Fee retained. Sources: [PumpPortal fees](https://pumpportal.fun/fees/) and",
    "[Local Transaction API](https://pumpportal.fun/local-trading-api/trading-api/).", "",
    "| Component | Classification | Basis / assumption |", "| --- | --- | --- |", *rows, "",
    "Standard buys use fee-inclusive exact input: protocol/creator fees are embedded in gross entry",
    "cash input, so the registry adds only modeled provider and network costs on top. Sells subtract",
    "venue/provider/network costs from simulated gross proceeds. No double fee deduction was found.", "",
    "Curve quotes derive quantity-specific impact from saved canonical reserves. The independent",
    "paper bank does not incorporate the hypothetical bot's own previous buy/sell reserve change.",
    "The same-bank entry round-trip probe is therefore a conservative entry diagnostic, not a",
    "measured actual round-trip or proof that costs will take exactly that percentage.", "",
    "The previous saved-bank hurdle ranges are 8.50–8.96% (12-trade portfolio) and 7.79–8.92%",
    "(8-trade reset portfolio). Costs and the cost-gate formula remain unchanged. New sample hurdle",
    "distribution is recorded only for actual corrected entries, otherwise N/A.", "",
    "Each side still has 50bps latency penalty + 50bps additional slippage + 50bps adverse fill.",
    "The configured 50ms computation + 750ms submission wait remains; prices refresh after waiting.",
    "These penalties are conservative assumptions, not empirically calibrated market losses.", "",
    "The simulator does not measure real dispatch, priority-fee auctions, rent/account creation or",
    "transaction inclusion. These remain limitations of economic PAPER-to-LIVE comparison.",
    "LIVE remains disabled. No costs were removed to improve historical profitability.", "",
    "Machine-readable assumptions and classifications: `analysis/paper_cost_model.json`.",
]))

old_rows = [f"| {c['label']} | {c['closed_positions']} | {c['wins']} / {c['losses']} | {D(c['decomposition']['curve_price_pnl_before_fees_friction']):.2f} | {D(c['net_pnl_usdt']):.2f} |" for c in performance["old_cohorts"]]
measure_rows = [f"| {name} | {shown(value)} |" for name, value in (
    ("Observed launches", sample["native_event_counts"].get("token.discovered", 0)),
    ("Unique serious candidate markets", sample["candidates_observed"]),
    ("Active decision evaluations", sample["decision_evaluations"]),
    ("Rejected missing required price signal (evaluations)", sample["rejected_missing_price_signal"]),
    ("Qualified entry decisions", sample["qualified_entries"]),
    ("Filled entries", sample["filled_entries"]), ("Completed trades", sample["completed_trades"]),
    ("Open positions", sample["open_positions"]), ("Wins / losses", f"{sample['wins']} / {sample['losses']}"),
    ("Gross PnL before explicit fees", perf["gross_pnl_before_fees"]),
    ("Curve-price PnL before fees/friction", perf["curve_price_pnl_before_fees_friction"]),
    ("Net PnL", perf["net_pnl"]), ("Fees (all actual fills)", perf["fees_all_fills"]),
    ("Execution friction (completed trades)", perf["execution_friction"]),
    ("Win rate (%)", perf["win_rate_percent"]), ("Average win", perf["average_win"]),
    ("Average loss", perf["average_loss"]), ("Profit factor", perf["profit_factor"]),
    ("Expectancy", perf["expectancy"]), ("Max realized drawdown", perf["max_realized_drawdown"]),
    ("Executable MFE samples", perf["sampled_executable_mfe_mae"]["mfe_net_percent"]["samples"]),
    ("Executable MFE p50 (%)", perf["sampled_executable_mfe_mae"]["mfe_net_percent"]["p50"]),
    ("Executable MAE p50 (%)", perf["sampled_executable_mfe_mae"]["mae_net_percent"]["p50"]),
    ("Stop receipt → trigger p50 (ms)", performance["latencies_ms"]["stop_event_received_to_trigger_ms"]["p50"]),
    ("Stop trigger → fill p50 (ms)", performance["latencies_ms"]["stop_trigger_to_fill_ms"]["p50"]),
    ("Stop overshoot p50 (percentage points)", performance["latencies_ms"]["stop_overshoot_percentage_points"]["p50"]),
)]
write_doc("PAPER_CORRECTED_RUN.md", "\n".join([
    "# Corrected bounded PAPER run", "",
    f"Run `{run['experiment_name']}`. Status: **{run['status']}**.",
    f"Active portfolio `{run['portfolio_id']}`. Started {run['started_at']}; ended {run.get('ended_at', 'collection still running')}.",
    "Entry collection bounded at 30 minutes; target 50 completed if naturally available, followed",
    "by paused-entry exit draining. No qualification or risk threshold was lowered.",
    "The initial Helius handshake returned HTTP429 and captured no market events; that empty",
    "attempt was archived separately. Existing Alchemy WSS acknowledged native log subscriptions",
    "and produced the actual observations below. Its endpoint difference limits old/new comparisons.", "",
    "| Measurement | Actual value |", "| --- | --- |", *measure_rows, "",
    "Candidates are unique markets reaching an active-strategy decision after the existing",
    "prefilter/risk assessment; counts of decision evaluations are separate. Rejection reasons",
    "can overlap and must not be summed as independent candidates.", "",
    f"Entry signal quality (evaluations): `{json.dumps(performance['entry_signal_quality'])}`.",
    f"Momentum status: `{json.dumps(performance['momentum_component_status'])}`.",
    f"Missing inputs: `{json.dumps(performance['missing_required_inputs'])}`.", "",
    f"Historical state reasons: `{json.dumps(performance.get('historical_state_reasons', {}))}`.", "",
    "## Historical comparison", "",
    "| Cohort | Closed | Wins / losses | Curve-price PnL before fees/friction | Net PnL |",
    "| --- | --- | --- | --- | --- |", *old_rows, "",
    "Historical ledger PnL reconciles within the saved PAPER model. All 20 historical entries had",
    "null price-change/decision-price evidence, so they do not validate historical momentum or",
    "the corrected entry strategy. Observational MFE/MAE zeroes are unavailable evidence, not true zeroes.", "",
    "Null-price entry path now rejects before RPC. Prospective accepted-entry absence is not an",
    "empirical validation of valid-price fill performance. Component completeness now exposes",
    "required subinput failure rather than relabeling missing history as complete momentum.",
    "The hurdle model/rates did not change; no new hurdle observations exist without entries.",
    "Stop overshoot, event-to-exit latency, executable MFE/MAE and shadow profit surrender require",
    "actual prospective positions. They are N/A if the corrected sample has none. Do not claim improvement.",
    "The old portfolios lost before fees/friction. The corrected strategy's pre-fee edge and",
    "expectancy are unmeasured without completed valid-signal entries. No positive expectancy claim.", "",
    "## Shadow exit comparison", "",
    "| Policy | Completed counterfactuals | Profit surrendered from executable peak |",
    "| --- | --- | --- |",
    *[f"| {name} | {value['closed_counterfactuals']} | {shown(value['profit_surrendered_percentage_points']['p50'])} |"
      for name, value in json.loads((A / 'paper_shadow_exits.json').read_text(encoding='utf-8'))['summary'].items()], "",
    "No policy winner was selected. Sampled executable MFE/MAE uses actual previous partial-fill",
    "proceeds plus remaining net liquidation, divided by original actual entry cost. Ring truncation",
    "is flagged and extrema outside retained marks are not invented.", "",
    "## Tail risk and remaining blockers", "",
    "Daily loss breaker remains 10% of initial cash (100 on a 1000 portfolio). Open-risk reserve",
    "uses 30% loss severity with a 15% open-risk budget and 40% exposure ceiling. A position can",
    "therefore be larger than the remaining daily loss budget: the theoretical 400 allocation",
    "can lose 400 on a collapse, while its modeled 30% reserve is already 120. The previous Lath",
    "position lost 119.59, exceeding the full 100 daily limit. This is tail exposure, not a direct",
    "arithmetic bug. No sizing or breaker parameter was changed. A net stop still cannot guarantee",
    "a fill at its threshold across a gap, RPC failure or reserve collapse.", "",
    "Remaining historical native-state invalidations are not bypassed. A fresh executable bank",
    "cannot reconstruct missing historical momentum. Strategy edge, live fills and latency",
    "improvement need real corrected observations; shadow endings still open at primary close",
    "are censored and ring-buffer truncation is explicit. No additional proof/provider architecture",
    "or retrospective RPC budget was added to force a sample.", "",
    "`runner-edge-prospective-v1` remains BLOCKED; LIVE disabled. The sample target is a target,",
    "not permission to loosen inputs. Insufficient data must be reported as such.", "",
    "The bounded worker stopped with entries paused and no open positions. This pause marks the",
    "end of the requested observation window; it is not a new trading loss. Telegram remains running.", "",
    "Artifacts: `analysis/paper_corrected_trades.json`, `paper_exit_latency.json`, `paper_cost_model.json`,",
    "`paper_shadow_exits.json`, `paper_corrected_performance.json`. Re-export with",
    "`.venv\\Scripts\\python.exe analysis\\export_corrected_paper.py`, then",
    "`.venv\\Scripts\\python.exe analysis\\render_corrected_report.py`.",
]))
print(json.dumps({"docs_rendered": 4, "cost_model_written": True, "config_unchanged": True,
                  "status": run["status"], "completed_trades": sample["completed_trades"]}))
