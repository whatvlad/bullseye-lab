# Bounded standard Pump.fun PAPER results

Experiment: `standard-pump-operational-paper-20261002-214954`. Status: **observing**.

Observation began 2026-10-02T21:49:54.778288+00:00; export/end 2026-10-02T23:28:42.960839+00:00.
Declared observation duration: continuous seconds; the run end timestamp also captures shutdown/drain.

The active existing strategy is aggressive. Entry thresholds, risk/alpha/Pulse qualification and configured local policy are preserved. Native discovery was explicitly approved. Live trading remained disabled.

| Measurement | Actual result |
|---|---|
| Observed native markets | 794 |
| Standard markets passing cheap scope screen | 439 |
| Serious candidate markets | 178 |
| Active strategy decisions | 461 |
| Paper trades entered | 1 |
| Paper trades completed | 1 |
| Open trades | 0 |
| Win rate (%) | 0 |
| Average win | N/A (insufficient completed evidence) |
| Average loss | -4.73272506 |
| Net completed PnL | -4.73272506 |
| Gross before fees | -2.929335856781712192734682234 |
| Profit factor | 0E+8 |
| Expectancy per trade | -4.73272506 |
| Maximum realized drawdown | 4.73272506 |
| All incurred fees | 1.803389203218287807265317766 |
| Completed-trade friction | 1.48877511177341339045090265 |
| Median holding seconds | 4 |
| Median executable MFE (%) | -8.963287178627403557380670230 |
| Median executable MAE (%) | -8.963287178627403557380670230 |
| Median entry-to-executable-peak seconds | 2.069809 |
| Local policy evaluations | 53 |
| Local policy vetoes | 28 |
| Local policy failures | 12 |

PnL and fees are in the configured portfolio currency. Completed-trade statistics exclude open exposure. Zero cash movement from zero fills is not evidence of a zero-risk or profitable strategy.

## Qualification and execution

Serious candidate markets are distinct mints receiving active strategy decisions after risk assessment. Repeated decisions do not count as new markets. Observed markets include cheap out-of-scope observations and are not all eligible launches.

Decision reasons (multiple reasons may apply to one decision):

```json
{
  "risk": 296,
  "risk_gate_not_approved": 254,
  "insufficient_observation_span": 217,
  "buyer_flow_concentrated": 205,
  "insufficient_trades_in_scoring_window": 190,
  "insufficient_unique_buyers_in_scoring_window": 155,
  "insufficient_sustained_buy_flow": 116,
  "ollama_model": 41,
  "llm": 41,
  "risk_score_unknown": 37,
  "ollama_unavailable_no_entry": 12,
  "buyer_attribution_incomplete": 4,
  "score_at_or_above_watch_threshold": 3,
  "score_below_watch_threshold": 2,
  "token_younger_than_strategy_minimum": 1
}
```

Execution rejection counts:

```json
{
  "entry_signal_expired": 7,
  "entries_paused": 4,
  "entry_signal_expired_before_fill": 1
}
```

## Required conclusions

1. The PAPER discovery/risk/strategy pipeline ran against real market data; exact fills are regression-validated. Natural fills were obtained.
2. Observed 794 markets; 178 serious candidate markets.
3. Entered 1 PAPER trades.
4. Completed 1 PAPER trades.
5. Win rate: 0.
6. Net completed PnL: -4.73272506.
7. Profit factor: 0E+8.
8. Expectancy: -4.73272506.
9. Maximum realized drawdown: 4.73272506.
10. Fees across all fills: 1.803389203218287807265317766; completed friction: 1.48877511177341339045090265.
11. Best setup: score segments are available in paper_performance.json; this small sample does not establish superiority.
12. Most costly failure: exit-reason segments are retained; the sample does not establish causality.
13. Positive expectancy: insufficient evidence from this bounded sample.
14. Next: extend the same frozen PAPER configuration and examine documented qualification and local-policy vetoes before proposing a profitability change. No threshold reduction is justified by this sample alone.

## Integrity limits

Rejected candidates retain decision features, score/risk snapshots, reasons and observational outcomes where available. A veto before final execution has no final fill bank or executable result; those fields remain null. After this measured window, additive telemetry was added to retain the already-read pre-risk curve/config bank for future candidates, without extra RPC or strategy changes. It cannot recover the unretained banks of this cohort; pre_risk_verification_bank is null here. Missing observational prices cannot support precise rejected-opportunity returns.

Old historical fills are not retroactively validated. This run does not establish profitability, executable historical MFE, source-disagreement calibration or live-trading readiness. The earlier runner-edge-prospective-v1 research experiment remains unactivated.

Entries are paused at bounded shutdown. Open exposure, if present, remains durable and requires continued monitoring; it is not reported as a synthetic closed position.

Artifacts: analysis/paper_trades.json, paper_candidates.json, paper_performance.json and paper_execution_assumptions.json. Validation: 457 tests, Ruff, mypy (135 source files).
