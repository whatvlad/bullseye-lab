# Strategy evidence — 1 October 2026

No entry/TP/SL thresholds were optimized in this audit. Current Conservative, Balanced and Aggressive presets remain versioned research hypotheses. Risk eligibility and emergency exits now constrain Ollama; its confidence value is not a calibrated return forecast. The wallet and risk score weights being zero does not disable hard risk vetoes.

## Measured feature relationships

`python -m memebot.research.features --train-end 2026-08-24T00:00:00+00:00 --validation-end 2026-08-26T00:00:00+00:00 --output docs/feature-statistics-2026-10-01.json`

The tool uses saved decision-time features and observed forward labels. It deduplicates the same feature across strategy comparisons, groups a token into its earliest temporal cohort, purges labels crossing split boundaries, and rejects future features. Missing labels, legacy unknown-quality labels, and late/gap labels are separate. See [the full report](feature-statistics-2026-10-01.json).

For the historical test cohort, only 1,004 of 5,109 eligible observations have an accepted five-minute label: 3,705 are missing and 400 are gaps. Those 1,004 observations represent **43 tokens**, not 1,004 independent trades.

| Feature, largest available window ≤30s | Pearson with 5-minute forward mark return | Observations / tokens |
|---|---:|---:|
| Unique-buyer rate acceleration | +0.02230 | 1,004 / 43 |
| Volume acceleration | +0.00541 | 1,004 / 43 |
| Price acceleration | +0.01603 | 1,004 / 43 |
| Buy/sell volume ratio | −0.00578 | 961 / 41 |

These simple relationships are weak in the accepted subset. They do not rule out nonlinear or regime-dependent information, and do not demonstrate net trading expectancy. Mean forward mark return of +4.03% in the first three rows is before costs, impact and fill delays and is subject to observation selection. It cannot be used as an expected edge for entries.

The training/validation histories largely predate explicit label-quality recording: 3,544 training and 38 validation five-minute labels have unknown quality and are excluded. This prevents honest training/validation comparison. A historical split labelled “test” is not prospective validation of changes made after inspecting those outcomes. Five-second labels were absent historically; they are now recorded for future sessions, not fabricated retroactively.

## Selection and missed opportunities

Stored five-minute key coverage (including labels whose quality may later be excluded): Aggressive entry candidates 1,276/1,766 versus skips 3,611/10,597; Balanced entry candidates 684/1,078 versus skips 4,211/11,343. Observation stops/candidate budgets and sampling therefore change coverage by action. Ranking rejected tokens against bought tokens without accounting for missing outcomes would be biased. The existing recorder stores skipped/watch decisions; research subscriptions retain a sampled control universe, not every market opportunity.

## Replay evidence

Two real incident tokens, 1,693 normalized events, 74 risk assessments and 222 current-preset decisions. Conservative: 74 skip. Balanced: 61 skip, 2 watch, 11 entry candidates. Aggressive: 65 skip, 2 watch, 7 entry candidates. Two outputs have SHA256 `2beb18aaab75d8ae8a14675000ab051a3122fb99a404f66248a64801a1030907`.

This counterfactual uses current deterministic presets and recorded risk/features in ingestion order. It validates repeatability and causal evidence selection, not profitability or complete live/paper execution parity. Entry candidates can repeatedly refer to the same token; they are not filled trades. It does not reconstruct Ollama output, transaction quotes, execution-time RPC reserve refreshes or portfolio exits. No replay PnL is reported.

## What research should happen next

1. Start an isolated prospective paper/shadow experiment with immutable configuration, complete causal market/reserve/conversion-price recording, funded/healthy data access and explicit request budgets.
2. Compare smaller risk-capped positions and retain all rejected candidates in a documented sampling scheme. A stop-loss cannot cap a crash loss.
3. Replay the full execution schedule and failed attempts through the same paper execution engine before testing earlier/later entries, exits and threshold changes.
4. Evaluate net expectancy, profit factor, tail losses, executable excursions, drawdown and outlier dependence on unseen sessions. Bootstrap by token/session rather than by correlated snapshots.
5. Only then consider wallet-score calibration, funding clusters, smart-wallet ablations, adaptive thresholds or regime-dependent sizing. Current funding/bundled-supply attribution remains unknown.

Funding clusters, creator-history causal validation, SOL-volatility regime series, profile-isolated paper portfolios, complete feature horizon reports for every proposed variable and executable counterfactual fills remain unfinished. This report does not claim a runner edge.
