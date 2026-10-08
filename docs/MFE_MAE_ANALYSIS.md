# Excursions, profit retention and loss concentration

Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. Production configuration, thresholds and trading state were not changed.

225 closed positions; 215 retained trade outcomes; 198 positions permit an observed tick excursion. 65 have bounded local gaps (MEDIUM), 160 LOW, zero verified HIGH histories. The 215 stored net-return outcomes span 200 tokens: mean -3.99%, win rate 32.56%, equal-return profit factor 0.724. This mixes versions/sizes/periods and is not portfolio return.

| Statistic | Observed MFE % | Observed MAE % |
|---|---|---|
| median | 4.28 | -12.48 |
| p25 | 0.00 | -21.79 |
| p75 | 28.13 | -3.11 |
| p90 | 50.10 | 0.00 |
| p95 | 59.63 | 0.00 |

48 of 125 losing positions with usable tick histories rose above actual entry fill price; 43 have positive stored MFE. These are mark gains, not proof of net executable profit. 18 of 73 winning positions with tick histories dipped more than 10% below entry. Tightening stops based on losers alone would ignore these winners.

| Group | N excursion rows | Median time to observed MFE, s | Median holding, s |
|---|---|---|---|
| losers | 125 | 6.89 | 40.80 |
| winners | 73 | 11.58 | 16.10 |

MFE/MAE start at zero at the fill. Recorded extrema can include RPC marks absent from trade history; times are only supplied when corresponding data exists. Gaps make extrema lower-bound observations and chronological dip-before-MFE ordering uncertain. Losing mark excursions do not establish that an exit was available. Optimal stop width, early profit taking and the typical time a true runner reveals failure are **INSUFFICIENT EVIDENCE**.

| Experiment | N losses | Largest/gross losses | Top 3/gross losses | Top 5/gross losses |
|---|---|---|---|---|
| Experiment: baseline-v3-fixed | 5 | 37.02 | 75.42 | 100.00 |
| Experiment: baseline-v1 | 11 | 23.98 | 53.80 | 74.32 |
| Experiment: sniper-v9-forward-2026-09-13 | 7 | 43.22 | 89.70 | 98.30 |
| Experiment: baseline-v5-fixed | 22 | 17.09 | 38.42 | 50.80 |
| Experiment: baseline-v2 | 43 | 6.26 | 17.36 | 26.50 |
| Experiment: baseline-v4 | 9 | 24.84 | 57.60 | 77.13 |

Tail concentration is unusually high in the latest run, but baseline-v2's largest loss is only 6.26% of gross losses. Tail control alone does not solve all historical selection problems. Removing the worst trade is a hindsight upper bound, not a tradable circuit breaker. Keep portfolios separate; USD/USDT capital, sizing and periods differ.

Reproduction: see [DATA_QUALITY.md](DATA_QUALITY.md). Machine-readable JSON and CSV are in `analysis/`.