# Age-matched runner feature and phase research

Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. Production configuration, thresholds and trading state were not changed.

| Age, s | Bought losers | Never-bought observed runners | Other | N HIGH |
|---|---|---|---|---|
| 10 | 1 | 5 | 2 | 0 |
| 20 | 2 | 9 | 3 | 0 |
| 30 | 2 | 7 | 2 | 0 |
| 60 | 2 | 3 | 2 | 0 |

Each token contributes once per age; windows are fixed at ten seconds. A feature must have arrived by the age checkpoint and be fresh. Risk is unavailable before its assessment time. Outcomes use the following 60s, not the features' future history. Only 1-2 bought losers survive per age. Median/quantile comparisons, Spearman ranks and seeded 500-replicate token bootstrap results are exported; bootstrap intervals are suppressed for groups under five. **No feature is established as separating bought losers from missed runners.**

Buyer/volume/price acceleration, flow ratio, reserve growth, unique buyers, trade frequency, concentration/HHI, liquidity, market cap, risk and runner score are covered where recorded. Last-5s/10s returns and observed VWAP distance are exported. Holder growth, verified profitable-wallet participation, linked-wallet/bundled supply and continuous creator activity lack usable histories. Unknown values stay null. Market cap uses the stated Pump supply assumption; native quote normalization and market changes limit comparability.

Useful hypotheses: pre-entry sell shock/large liquidity-relative sell, adverse velocity, return from first observation and divergence across 10s/60s windows. FLETCH supports asking these questions, not a production cutoff. The previous weak five-minute linear relationships do not prove acceleration features useless. **INSUFFICIENT EVIDENCE** to declare any existing feature generally useless. Zero-weight wallet/social components could not explain these entry score decisions, which used momentum and graduation velocity.

Research phases in the worst-trade timeline: EARLY_EXPANSION if price velocity, buyer and volume acceleration are positive; OVEREXTENDED if price rises without positive buyer acceleration; DISTRIBUTION/FAILED if the research failure signals appear; IGNITION/WATCHING otherwise. UNKNOWN when inputs are missing. These annotations can switch rapidly. CONFIRMED_RUNNER and DEAD require persistence/coverage that these histories do not prove. The phase model is not calibrated or enabled, and no tree model was fitted to a 1-2-loser comparison panel. Multiple testing, regimes, strategy versions and selected follow-up prevent causal conclusions.

Reproduction: see [DATA_QUALITY.md](DATA_QUALITY.md). Machine-readable JSON and CSV are in `analysis/`.