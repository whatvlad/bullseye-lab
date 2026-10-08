# Candidate proof readiness

**Architecture implemented; runner BLOCKED; synchronized calibration not ready.**
No live trading, paper positions or strategy experiment was started. Database
counts and trading controls remained identical to the recorded baseline. Strategy
thresholds and disagreement bands were unchanged.

| Question | Answer |
|---|---|
| 1. Can a serious standard candidate obtain bounded proof? | The API and encoded buy/sell PASS paths work. No live candidate passed yet. |
| 2. Required evidence? | Canonical mint/curve/vault and owner/supply/quote/mode/completion; atomic Global/FeeConfig/creator bindings; bounded native sequence, physical invariants and exact quantity/fee parity; fresh order-time state. |
| 3. Average/p90 RPC cost? | 2.444 / 3 reads over nine rejected live attempts; 22 total. Successful complete live cost is unknown. |
| 4. Proof latency? | Average 274.783 ms; median 262.818; p90/max 381.954. |
| 5. Common failures? | Five unvalidated fee-route failures; four missing-anchor continuity failures. |
| 6. Tier selection/rounding validated? | 108 official SDK comparisons and encoded native buy/sell tests pass. Live native parity remains unvalidated. |
| 7. Candidate-time identity/config valid? | One bank batch verifies supported candidate bindings; this alone does not establish execution readiness. The detailed capture has a coherent supported binding but no anchored path. |
| 8. Is execution refresh cheap? | One batch with stable-version/cache checks; proven in tests, not yet measured after a live PASS. |
| 9. Ready for standard-only synchronized calibration? | No. Need successful live anchored proofs, validated applicable fee routes and live both-side parity/refresh evidence. |
| 10. Can the runner begin if calibration passes? | Not automatically. All prerequisite/risk/price gates and integration of refreshed validated quotes into paper orders must pass. This task does not authorize activation. |

The remaining blockers concern the narrow standard cohort: signature-index lag or
bounded-window incompleteness, unvalidated ordinary cashback/reward/shared fee
routing, no successful live native/refresh proof, and representative synchronized
candidate calibration. These must not be replaced by slot-only disagreement
samples or static fee assumptions. No bands were configured.

The eight retained standard divergences remain causally unresolved. They are
forensic regression inputs; known divergence and unexplained physical mutation
cannot approve a prospective proof. Historical causality is not required for this
architecture, and the old failures do not justify unbounded history research.

Required artifacts:

- `analysis/candidate_execution_proofs.json`: all nine attempts, timing, slots,
  available account/history evidence, quotes, failures and both capture references.
- `analysis/standard_fee_validation.json`: SDK provenance, comparison cases and
  live parity limitation.
- `analysis/candidate_proof_cost.json`: per-attempt duties and rejection costs.
- `analysis/candidate_proof_gate.json`: BLOCKED gate, source/evidence hashes,
  unchanged database/control verification and regression results.

The first capture predates richer rejected-attempt retention. Its known account
slots are recovered from the original RPC context logs and explicitly labeled;
they are not retrospectively called execution-synchronized. The second capture
retains detailed rejected state/history and research quotes. No rejected packet
was promoted to execution readiness.
