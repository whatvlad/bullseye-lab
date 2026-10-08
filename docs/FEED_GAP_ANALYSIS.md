# Historical open-position feed gaps

Source snapshot: 2026-10-01 07:27:25 UTC. Read-only analysis script: [price_prerequisite_audit.py](../analysis/price_prerequisite_audit.py). [Aggregate JSON](../analysis/feed_gap_analysis.json), [per-position CSV](../analysis/feed_gap_positions.csv). Input SHA256 checks cover positions, trade outcomes, orders and trades.

225 closed positions across historical portfolios; 198 have at least one observed in-position same-market tick. For all positions, silence is measured by **provider receipt timestamps**, with entry and close boundaries included. 27 positions have no in-position ticks: their entire holding interval is unobserved, not a zero-gap stable price. These intervals are included in the counts. A gap is strictly greater than its stated limit. 215 positions have recorded percentage outcomes; 10 do not, and are omitted from percentage statistics.

| Receipt silence | Positions | Wins / losses | Pooled recorded PnL | Median recorded return | Losses below -30% / known returns |
|---|---:|---:|---:|---:|---:|
| >1 second | 170 | 56 / 114 | -331.6762 | -8.9544% | 20 / 161 |
| >5 seconds | 111 | 31 / 80 | -332.5899 | -10.3230% | 19 / 103 |
| >10 seconds | 95 | 24 / 71 | -312.0095 | -10.6844% | 19 / 88 |
| >30 seconds | 74 | 19 / 55 | -166.6712 | -9.8457% | 13 / 67 |
| >60 seconds | 62 | 16 / 46 | -86.9126 | -7.7135% | 9 / 55 |

Pooled PnL mixes recorded USD/USDT portfolios, starting capital, versions and dates. It is descriptive arithmetic, not portfolio return or strategy EV. Rows overlap and must not be summed. The -30% cutoff is an analysis label for extreme recorded losses, not a new strategy parameter.

There is descriptive association in several comparisons: >5-second group had 19/103 (18.45%) extreme losses versus 7/112 (6.25%) at or below 5 seconds. At 10 seconds it was 19/88 (21.59%) versus 7/127 (5.51%); at 60 seconds it was 9/55 (16.36%) versus 17/160 (10.63%). The relationship is not monotonic: the >60-second group's mean recorded return was +1.4995%, versus -5.8797% for shorter intervals. Per-portfolio splits are retained in JSON.

These data do not establish causal feed failures. Longer-held positions have more opportunities for gaps; illiquidity, strategy/version, market state, capture coverage and capital confound results. Sparse trading can create silence without a failed provider. Source-event times for PumpPortal are estimated; this analysis measures observation availability, not independently verified chain age. Unreconciled stream/RPC states also undermine the outcome labels themselves. No significance or predictive calibration claim is made.

Cappuccinu had a 268.81-second receipt gap and a -67.08% booked result, but the long gap ended approximately 16 minutes before the close. Its final receipt was only 0.45 seconds old. FLETCH's extreme booked loss occurred with a much shorter holding interval. Gaps alone cannot explain all tail losses or distinguish the causes of these two trades.
