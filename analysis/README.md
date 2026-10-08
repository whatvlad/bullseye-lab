# Runner research — 1 October 2026

This is historical, exploratory research. No production thresholds or trading controls were changed. No live trading or new paper experiment was started.

- [Two worst trades](../docs/WORST_TRADES_FORENSICS.md): complete event/feature/decision/order timelines and evidence-based failure classification.
- [Excursions and tails](../docs/MFE_MAE_ANALYSIS.md): observed versus recorded MFE/MAE, missing timestamps, distributions and per-portfolio loss concentration.
- [Missed runners](../docs/MISSED_RUNNERS.md): never-bought tokens, coverage, profile-specific blockers and exact stored configuration versions.
- [Entry, observation and costs](../docs/ENTRY_TIMING_ANALYSIS.md): all requested entry offsets, observation ages and position sizes; rejected counterfactuals stay rejected.
- [Exit timing](../docs/EXIT_TIMING_ANALYSIS.md): earliest causal failure flags and limitations of potential avoided-loss calculations.
- [Features and phases](../docs/RUNNER_FEATURE_STUDY.md): equivalent-age comparisons, robust statistics and research-only lifecycle annotations.
- [Data quality](../docs/DATA_QUALITY.md): sample sizes, quality dimensions, source hashes and reproduction commands.
- [Frozen proposal](../docs/NEXT_EXPERIMENT.md): paired PAPER/SHADOW hypothesis; not activated.

Every table has JSON and CSV counterparts. `summary.json` contains aggregate panels; `source_manifest.json` identifies the immutable raw capture. Raw history is preserved under ignored `research_sessions/strategy-2026-10-01/`.

`conditional_two_state_return_percent` is a mathematical sensitivity result whose baseline could not be reconciled. It is **not** net tradable expectancy. Peak labels are hindsight mark labels, not optimal executable exits. Missing values remain null/blank. Repeated positions and cross-profile decisions do not create independent token samples.

The two standalone ReportLab figures show observations as blue points and paper fills as red points. Gaps are deliberately not joined:

- [FLETCH trajectory](FLETCH-trajectory.svg)
- [Cappuccinu trajectory](cappuccinu-trajectory.svg)

To regenerate figures on this machine after generating research outputs:

```powershell
& 'C:\Users\shiro\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' analysis/create_figures.py
```

The bundled runtime supplies ReportLab. No chart dependency was installed into the trading application's environment. `next_experiment.json` includes canonical configuration hash, frozen strategy/settings and runtime code hashes. Its start timestamp remains null.
