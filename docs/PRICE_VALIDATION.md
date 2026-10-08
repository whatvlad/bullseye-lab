# Runner prerequisite validation

The subsequent passive [market-data calibration](MARKET_DATA_CALIBRATION.md) also remains
BLOCKED. Experiment creation now requires both gates to pass, including representative
calibration coverage. The pilot measured large disagreements but did not justify safety bands.

Status: **BLOCKED — `runner-edge-prospective-v1` has not started.** No live trading enabled. Strategy score, sizing, stop and runner thresholds unchanged. Actual `.env` and experiment/portfolio controls were not changed by this pass.

Implemented and covered by regression tests: explicit price provenance, execution-oriented fills and net marks, no implicit freshness from missing events, configurable entry blocks, dedicated exit RPC fallback, fresh stream reserve fallback for exits, recovery after unavailable currency quotes, exit priority, separation of stream excursions from execution marks, stale-mark UI, and fail-closed experiment startup.

`ExperimentRepository.start` rejects this specific prospective name before database mutation unless `analysis/price_validation.json` records all prerequisite checks passed, matches every critical code fingerprint and the current safety configuration. Missing, blocked, malformed or outdated evidence blocks startup. The frozen earlier proposal is retained; it does not grant startup permission after these execution-model changes.

## Remaining blockers

1. `paper_entry_max_source_disagreement_percent` is intentionally unconfigured. No permanent disagreement limit can be inferred from the available history. Unconfigured or unknown comparison blocks entries, including manual paper buys. Choose and freeze an operational safety limit on defensible simultaneous observations; test fixture values are not recommendations.
2. Actual prospective stream/RPC freshness and simultaneous reserve reconciliation are not operationally verified in this pass. PumpPortal source times are receipt estimates without comparable slots. Strict default policy blocks estimated feed source times. A recent RPC receipt also does not independently prove current chain state; slot regression protection alone is insufficient evidence against lagged/cached account data.
3. Fee/creator configuration and exact PumpSwap execution fidelity remain conditional. Local simulations are labeled estimated; external executable quote/transaction-simulation validation is absent. Capture and validate those assumptions before treating prospective results as execution evidence of strategy edge.
4. Legacy PnL/MFE cannot be promoted to verified executable outcomes. Old open positions, if any, require fresh complete execution marks before new exposure is allowed. Historical rows remain untouched.

An additive migration `20261001_0016` adds nullable execution-mark evidence to paper positions. It does not rewrite historical prices, fees, outcomes or control settings. The separate validation artifact records migration/verification results.

The permitted outcome of this bounded pass is tested safeguards plus an explicit blocked gate. No worker, paper experiment, trade or paid trade-feed probe was started. Activation requires a subsequent operational validation that resolves these evidence/configuration blockers; even a passing artifact does not automatically activate the run.

Verification: regression suite, Ruff and strict Mypy pass (101 source files). PostgreSQL migration `20261001_0016` applied; 225 positions, 1,826 orders, 215 outcomes, 18 portfolios, 10 prior experiments and 29 strategy configurations retained. Strategy controls match the pre-migration snapshot. No open positions and no row for the prospective runner experiment. See [validation artifact](../analysis/price_validation.json) for exact test count and code fingerprints and [database validation](../analysis/price_database_validation.json).
