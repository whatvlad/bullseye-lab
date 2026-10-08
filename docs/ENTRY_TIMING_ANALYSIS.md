# Entry timing, observation and size sensitivity

Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. Production configuration, thresholds and trading state were not changed.

| Entry offset, s | N total | N usable | N HIGH | Conditional mean net % | PF |
|---|---|---|---|---|---|
| -5 | 225 | 1 | 0 | -8.32 | 0.00 |
| -3 | 225 | 2 | 0 | -15.46 | 0.00 |
| -1 | 225 | 2 | 0 | -18.39 | 0.00 |
| 0 | 225 | 2 | 0 | -18.90 | 0.00 |
| 1 | 225 | 1 | 0 | -21.65 | 0.00 |
| 3 | 225 | 2 | 0 | -19.81 | 0.00 |
| 5 | 225 | 0 | 0 | UNKNOWN | UNKNOWN |
| 10 | 225 | 2 | 0 | -19.52 | 0.00 |

No position is usable at **all eight offsets**; the common panel is zero. Usable cells contain only 0-2 positions and different survivors. There is no basis to choose an offset. The broader claim 'the bot generally enters too late' is **INSUFFICIENT EVIDENCE**. FLETCH was late relative to its first observed expansion; Cappuccinu was not the same chase.

Conditional simulations hold exit decision fixed and do not reconstruct dynamic exits/partials. They use the same PaperFillSimulator, .05 SOL standard stake, 800ms delay, 50bps adverse latency adjustment per side, modeled venue/service/network/priority fees. Require recorded real reserves, fresh causal ticks, same market, Pump.fun/WSOL and ≤300bps modeled impact. A historical RPC exit-mark mismatch above 5% invalidates net timing/avoided-loss claims; the mathematical two-state result stays in a separately named column. This is a research reconciliation tolerance, not a trading threshold.

| Observation age, s | N tokens | N conditional simulations | N HIGH |
|---|---|---|---|
| 1 | 8245 | 9 | 0 |
| 2 | 8245 | 8 | 0 |
| 3 | 8245 | 8 | 0 |
| 5 | 8245 | 15 | 0 |
| 8 | 8245 | 14 | 0 |
| 10 | 8245 | 15 | 0 |
| 15 | 8245 | 23 | 0 |
| 20 | 8245 | 22 | 0 |
| 30 | 8245 | 19 | 0 |

Each age uses only a feature received by that time, no older than two seconds, then a fixed 60-second conditional holding period. These are not existing-strategy decisions or an optimized observation window. Small surviving panels and candidate-only reserve coverage produce large apparent gains in some cells; those are selection-biased and do not demonstrate an early-runner edge. A useful observation duration is **INSUFFICIENT EVIDENCE**.

| Size SOL | N usable positions | Conditional mean net % | No-impact break-even % |
|---|---|---|---|
| 0.01 | 2 | -20.36 | 6.90 |
| 0.025 | 2 | -19.23 | 5.53 |
| 0.05 | 2 | -18.90 | 5.07 |
| 0.1 | 2 | -18.85 | 4.84 |
| 0.25 | 2 | -19.16 | 4.70 |
| 0.5 | 2 | -19.82 | 4.66 |

Analytic friction floors are not empirical expectancy and exclude impact, rent and token extensions. Jito baseline is zero because no Jito path exists; an additional 0.0001 SOL tip each side is a separate labelled stress scenario, not an observed Jito fee. Minimum economically sensible and maximum profitable size are **INSUFFICIENT EVIDENCE**. Larger size reduces fixed-cost proportion but increases impact.

| Entry expansion from first observed trade | N net outcomes | Mean net % |
|---|---|---|
| -10000_to_0 | 38 | -10.26 |
| 0_to_20 | 76 | -4.33 |
| 20_to_40 | 19 | 13.82 |
| 40_to_60 | 6 | -3.33 |
| 60_to_100 | 10 | -13.35 |
| 100_to_1000000 | 24 | -15.52 |

The ≥60% groups look worse descriptively; the 20-40% group is positive. This is neither monotonic nor age/version matched, includes repeated tokens, and has unknown discovery prices. No chasing cutoff was fitted. Last-5s/10s return and 10s observed VWAP distance are recorded for future testing, not introduced into production.

Reproduction: see [DATA_QUALITY.md](DATA_QUALITY.md). Machine-readable JSON and CSV are in `analysis/`.