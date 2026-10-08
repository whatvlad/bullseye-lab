# Failure-signal and exit timing study

Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. Production configuration, thresholds and trading state were not changed.

Research signals use the saved 10-second rolling window: (1) latest-trade return ≤-5% with latest sell ≥5% of real quote liquidity; (2) negative buyer acceleration together with negative flow imbalance; (3) negative reserve velocity together with negative price velocity. The numeric shock cutoffs are research definitions; none were enabled. Absent reserve/wallet values do not satisfy a signal.

| Signal | Positions with post-entry flag | Usable avoided-return comparisons | N HIGH |
|---|---|---|---|
| large_sell_with_price_shock | 7 | 1 | 0 |
| buyer_deceleration_and_net_selling | 58 | 2 | 0 |
| reserves_and_price_falling | 10 | 2 | 0 |

For FLETCH all three first post-entry flags appeared about 1.38s before exit. That leaves little execution headroom; its pre-entry shock is the more relevant hypothesis. For Cappuccinu the first buyer/flow warning appeared 2,071.57s before exit, reserve/price warning 2,149.36s before, and large-sell shock 643.47s before. These can precede substantial recovery: treating the earliest flag as certain failure is unjustified. Its unreconciled exit mark prevents a credible USDT avoided-loss calculation.

| Pre-entry flag | Losers flagged | Winners flagged | N snapshots available |
|---|---|---|---|
| large_sell_with_price_shock | 1 | 0 | 215 |
| buyer_deceleration_and_net_selling | 4 | 1 | 215 |
| reserves_and_price_falling | 2 | 0 | 215 |

Pre-entry sell shock flags one loser and zero winners; buyer/flow flags four losers and one winner. These sparse counts are hypotheses, not estimates of stable sensitivity or profit improvement. The latest catastrophic exits had stop signals; 'no stop' is not the observed failure. General exit lateness, optimal TP/SL, and avoided loss are **INSUFFICIENT EVIDENCE**. Counterfactual return deltas are conditional equal-size two-state comparisons, not dollar savings or full execution replay.

Reproduction: see [DATA_QUALITY.md](DATA_QUALITY.md). Machine-readable JSON and CSV are in `analysis/`.