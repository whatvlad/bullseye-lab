# Next frozen prospective paper experiment

**Price prerequisite gate: BLOCKED.** The subsequent bounded prerequisite pass added execution-evidence controls without changing strategy thresholds. The frozen proposal below remains unstarted; its prior runtime fingerprints are historical references. See [PRICE_VALIDATION.md](PRICE_VALIDATION.md) and `analysis/price_validation.json` for current code/configuration validation and unresolved source-integrity blockers.

Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. Production configuration, thresholds and trading state were not changed.

**PROPOSED, NOT STARTED.** Experiment `runner-edge-prospective-v1`; canonical configuration SHA256 `d3dddefb723ccbfd0589c4bb3ee6ece8f31622e43b0069125458f739209e1909` in `analysis/next_experiment.json`. Start time remains null until activation; no active experiment or entry controls were changed.

Question: does vetoing a fresh large-sell/price-shock entry improve after-cost paired expectancy without rejecting too many future winners? This is the highest-priority strategy hypothesis because it was visible before FLETCH's catastrophic fill. Its expected value is not established from one flagged loser.

Arm A: current frozen Aggressive presets and existing exits. Arm B: identical feed, stake and decisions, with a research-only latest-trade ≤-5% plus sell/real-liquidity ≥5% veto. Log the flag in shadow first. These cutoffs are a preregistered hypothesis, not an endorsed production change. Unknown inputs cannot become a veto/approval. Retain the other two profiles as observation-only comparisons.

Use independent paper ledgers, .05 SOL standard stakes, the exact saved execution assumptions and a 300bps research impact cap. Standardizing a stake controls the comparison; it is not an optimized size. Existing 30-40% portfolio exposure is unsuitable for isolating signal quality. No signer or LIVE mode.

Before activation: verify funded trade access or validated native feed, resolve stream/RPC price consistency, preserve complete causal quote/reserve/FX evidence, and provide separate arm accounting. The current research code does not run these two portfolios or claim execution parity. Implement only this bounded experiment support when launching it.

Minimum 14 days, 1,000 candidates, 100 completed baseline trades and 100 independent trade tokens; continue until all are met, with a 30-day underpowered-review boundary. These are minimum operational targets, not proof of statistical power against rare catastrophes. No parameter changes mid-run. Any change starts a new experiment/hash.

Primary: paired net PnL per baseline opportunity, with arm-B vetoes counted as zero trades and every eligible baseline token retained. Cluster uncertainty by token/session. Also report EV, PF, drawdown, tail loss, false vetoes, missed executable runners, latency, slippage/fees/impact and quality. Fixed hash-sampled rejected controls must be selected before returns are known; save sampling probabilities. No cherry-picked runner cohort.

Pause on critical missing/stale data or reserve/stream disagreement; stop on accounting inconsistency, accidental live configuration, or 10% arm paper drawdown. Diagnose without retuning. Positive paired results still require another unseen frozen run and complete cost reconciliation. Otherwise state **INSUFFICIENT EVIDENCE**.

Reproduction: see [DATA_QUALITY.md](DATA_QUALITY.md). Machine-readable JSON and CSV are in `analysis/`.
# Market-data calibration remains BLOCKED

The passive pilot is recorded in [MARKET_DATA_CALIBRATION.md](MARKET_DATA_CALIBRATION.md).
It collected 180 pairs across 8 tokens at a 200-request cap. No runner experiment was started.
The calibration gate and price prerequisite gate must both pass before activation.
