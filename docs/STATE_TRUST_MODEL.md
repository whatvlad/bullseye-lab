# State trust model and readiness

Observational trust, canonical identity, config facts, execution assumptions and state divergence are independent dimensions. `NormalizedMarketState.evidence()` and serialized paper-fill evidence expose those dimensions. The legacy HEALTHY execution gate is retained only for complete proven execution prerequisites; it does not replace the independent flags.

| Dimension | Requirement / use |
|---|---|
| OBSERVATIONAL_HEALTHY | Proven normalized reserve semantics plus FIRST/EXACT/RPC_VALIDATED continuity; momentum may use the reserve price |
| OBSERVATIONAL_INCOMPLETE / UNKNOWN | Missing/ambiguous history; reserve-dependent features are unavailable, not zero or stable |
| EXECUTION_IDENTITY_VERIFIED | Canonical account bindings actually pass; can be invalidated independently |
| EXECUTION_CONFIG_VERIFIED | Bound on-chain config version decoded; no claim of exact fee application |
| execution_assumptions_verified | Exact executable assumptions additionally proven; remains false |
| DIVERGED | Nonzero integer residual; local repair required |

Repairs are market-coalesced and admitted by duty/budget. Stable ticks cannot erase a broken history. An older RPC slot cannot overwrite newer stream state. Reserve repair restores only what was proved. Open-position exits retain their prioritized RPC fallback path and cannot use rejected/degraded RPC as a valid simulated fill. No worker, order, paper position or experiment was started in this pass.

Final passive capture: **61.94s**, **18,303 trades**, **746 markets**, capped at 150,000 native messages. Counts: FIRST 745, EXACT 6, DIVERGED 618, UNKNOWN 16,934. UNKNOWN attribution: POOL 12,613; MARKET 3,958; VENUE 363; GLOBAL 0. There are 778 coalesced pending repairs; 12 admitted bootstraps, 11 accepted reconciliations. Successful bootstrap proof and current trust are deliberately separate.

RPC: **37 calls / 12 candidates = 3.0833 per candidate**, **0.6066 per observed launch**, no per-event calls. The 37 comprise 13 shared config batches and 24 curve/identity reads. Across the bounded forensic sample, initial validation, final capture and supplemental stricter canonical checks: **82 read-only Solana requests**. Three public schema downloads are separate. No new disagreement bands or strategy thresholds were configured.

The old capture (3,962 trades, 94 EXACT, 117 DIVERGED, 3,323 UNKNOWN) and new capture are different sessions/durations. The retained same-coverage replay reproduces all local statuses exactly and shows **0 UNKNOWN reduction caused by scope alone**. Narrowing prevents cross-market collateral invalidation but unresolved silent native self-CPIs still occur on nearly every traded market. No better feed reliability is claimed.

| Readiness question | Evidence-based answer |
|---|---|
| Cause of the 117 Pump.fun mismatches | Isolated virtual-quote changes; sampled evidence supports a recurring Mayhem link; exact causal mechanism unproven |
| Remaining UNKNOWN | 117 forensic causal mechanisms; separately 16,934 UNKNOWN observations in the new capture |
| Global invalidation eliminated | No global reserve invalidations/UNKNOWN in this capture; 18 necessary global config-only invalidations remain |
| Single-market scoping | 18,806 / 19,616 active invalidations = 95.87% |
| Pump.fun canonical identity | 12 sampled bootstraps pass; later uncertainty invalidates current trust |
| PumpSwap canonical identity | Three sampled pools pass final canonical/migration/vault checks |
| Fee/config inputs verified | Four global/fee accounts, full schedules, flags, authorities and byte-hash versions at source slots |
| Still estimated/unproven | Actual tier/routing/rounding, extensions, slippage/fees and synchronized execution state |
| RPC per candidate | 3.0833 in final passive capture; cold pool bootstrap requires extra binding reads |
| Synchronized disagreement calibration ready | Bounded transaction-reconstruction research can proceed; broad synchronized calibration is not yet trustworthy |
| runner-edge-prospective-v1 | **BLOCKED** |

Remaining blockers: silent CPI instruction data is absent from live logs; exact Mayhem virtual-state boundary is unproven; direct vault changes and loss layer are not comprehensively captured; RPC is SLOT_ONLY rather than transaction/state-sequence synchronized; per-order fee/execution assumptions remain incomplete; representative synchronized residual evidence is insufficient; disagreement bands stay intentionally unconfigured. Historical PnL is not retroactively repaired or promoted by these new proofs.

Evidence: the five requested JSON reports, `pumpfun_multi_event_reconstruction.json`, and `state_trust_verification.json`. Regression coverage includes local/venue/global invalidation, original cause retention, canonical mismatch, config version/cache change, reserve-only repair, multi-event ambiguity, incomplete-entry refusal and safe observational features.
