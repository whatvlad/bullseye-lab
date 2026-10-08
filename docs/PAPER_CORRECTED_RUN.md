# Corrected bounded PAPER run

Run `standard-pump-paper-corrected-20261003-140803`. Status: **complete**.
Active portfolio `b081c304-e142-43cf-b229-cf20d0164dec`. Started 2026-10-03T14:08:03.865872+00:00; ended 2026-10-03T14:38:16.652764+00:00.
Entry collection bounded at 30 minutes; target 50 completed if naturally available, followed
by paused-entry exit draining. No qualification or risk threshold was lowered.
The initial Helius handshake returned HTTP429 and captured no market events; that empty
attempt was archived separately. Existing Alchemy WSS acknowledged native log subscriptions
and produced the actual observations below. Its endpoint difference limits old/new comparisons.

| Measurement | Actual value |
| --- | --- |
| Observed launches | 424 |
| Unique serious candidate markets | 96 |
| Active decision evaluations | 449 |
| Rejected missing required price signal (evaluations) | 449 |
| Qualified entry decisions | 0 |
| Filled entries | 0 |
| Completed trades | 0 |
| Open positions | 0 |
| Wins / losses | 0 / 0 |
| Gross PnL before explicit fees | 0 |
| Curve-price PnL before fees/friction | 0 |
| Net PnL | 0 |
| Fees (all actual fills) | 0 |
| Execution friction (completed trades) | 0 |
| Win rate (%) | N/A — no completed trade evidence |
| Average win | N/A — no completed trade evidence |
| Average loss | N/A — no completed trade evidence |
| Profit factor | N/A — no completed trade evidence |
| Expectancy | N/A — no completed trade evidence |
| Max realized drawdown | N/A — no completed trade evidence |
| Executable MFE samples | 0 |
| Executable MFE p50 (%) | N/A — no completed trade evidence |
| Executable MAE p50 (%) | N/A — no completed trade evidence |
| Stop receipt → trigger p50 (ms) | N/A — no completed trade evidence |
| Stop trigger → fill p50 (ms) | N/A — no completed trade evidence |
| Stop overshoot p50 (percentage points) | N/A — no completed trade evidence |

Candidates are unique markets reaching an active-strategy decision after the existing
prefilter/risk assessment; counts of decision evaluations are separate. Rejection reasons
can overlap and must not be summed as independent candidates.

Entry signal quality (evaluations): `{"OBSERVATIONAL_INCOMPLETE": 448, "OBSERVATIONAL_HEALTHY": 1}`.
Momentum status: `{"INCOMPLETE": 449}`.
Missing inputs: `{"decision_price": 448, "price_provenance": 448, "price_window_coverage": 449, "rolling_price_change": 448}`.

Historical state reasons: `{"UNKNOWN_NATIVE_INSTRUCTION": 448, "trade_only_coverage_requires_rpc": 1}`.

## Historical comparison

| Cohort | Closed | Wins / losses | Curve-price PnL before fees/friction | Net PnL |
| --- | --- | --- | --- | --- |
| previous | 12 | 1 / 11 | -164.78 | -219.00 |
| current | 8 | 1 / 7 | -223.80 | -266.90 |

Historical ledger PnL reconciles within the saved PAPER model. All 20 historical entries had
null price-change/decision-price evidence, so they do not validate historical momentum or
the corrected entry strategy. Observational MFE/MAE zeroes are unavailable evidence, not true zeroes.

Null-price entry path now rejects before RPC. Prospective accepted-entry absence is not an
empirical validation of valid-price fill performance. Component completeness now exposes
required subinput failure rather than relabeling missing history as complete momentum.
The hurdle model/rates did not change; no new hurdle observations exist without entries.
Stop overshoot, event-to-exit latency, executable MFE/MAE and shadow profit surrender require
actual prospective positions. They are N/A if the corrected sample has none. Do not claim improvement.
The old portfolios lost before fees/friction. The corrected strategy's pre-fee edge and
expectancy are unmeasured without completed valid-signal entries. No positive expectancy claim.

## Shadow exit comparison

| Policy | Completed counterfactuals | Profit surrendered from executable peak |
| --- | --- | --- |
| CURRENT_POLICY | 0 | N/A — no completed trade evidence |
| EARLIER_PROFIT_PROTECTION | 0 | N/A — no completed trade evidence |
| DEFENSIVE_PROFIT_PROTECTION | 0 | N/A — no completed trade evidence |

No policy winner was selected. Sampled executable MFE/MAE uses actual previous partial-fill
proceeds plus remaining net liquidation, divided by original actual entry cost. Ring truncation
is flagged and extrema outside retained marks are not invented.

## Tail risk and remaining blockers

Daily loss breaker remains 10% of initial cash (100 on a 1000 portfolio). Open-risk reserve
uses 30% loss severity with a 15% open-risk budget and 40% exposure ceiling. A position can
therefore be larger than the remaining daily loss budget: the theoretical 400 allocation
can lose 400 on a collapse, while its modeled 30% reserve is already 120. The previous Lath
position lost 119.59, exceeding the full 100 daily limit. This is tail exposure, not a direct
arithmetic bug. No sizing or breaker parameter was changed. A net stop still cannot guarantee
a fill at its threshold across a gap, RPC failure or reserve collapse.

Remaining historical native-state invalidations are not bypassed. A fresh executable bank
cannot reconstruct missing historical momentum. Strategy edge, live fills and latency
improvement need real corrected observations; shadow endings still open at primary close
are censored and ring-buffer truncation is explicit. No additional proof/provider architecture
or retrospective RPC budget was added to force a sample.

`runner-edge-prospective-v1` remains BLOCKED; LIVE disabled. The sample target is a target,
not permission to loosen inputs. Insufficient data must be reported as such.

The bounded worker stopped with entries paused and no open positions. This pause marks the
end of the requested observation window; it is not a new trading loss. Telegram remains running.

Artifacts: `analysis/paper_corrected_trades.json`, `paper_exit_latency.json`, `paper_cost_model.json`,
`paper_shadow_exits.json`, `paper_corrected_performance.json`. Re-export with
`.venv\Scripts\python.exe analysis\export_corrected_paper.py`, then
`.venv\Scripts\python.exe analysis\render_corrected_report.py`.
