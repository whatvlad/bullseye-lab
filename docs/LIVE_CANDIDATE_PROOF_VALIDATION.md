# First live candidate proof validation

The first real passive candidate PASS was obtained on 2 October 2026 at 00:50:29 Dublin time (1 October 23:50:29 UTC). The runner remains BLOCKED. No orders or positions were created.

Candidate mint: `F57hJHhuG6ryRYNPncoN34xR31pn9r9b3Pbi2odtEQ7v`.
Native signature: `rLdSYWuQEG4mGTNoum6QX2R6TEHfHceDGeqiex9PqhaEuwqSgcKDH8qxJqSoRg7ukcvxshwSk5XzZLDKE5qWSn9`.
Atomic identity/reserve/config bank: slot `452440138`. Native side: SELL. Route: STANDARD_SIMPLE_FEE_ROUTE, including the protocol buyback split. Its native anchor was absent from the address index throughout the history fences.

The proof verifies standard non-Mayhem Pump.fun, SOL quote, a single supported native transaction, canonical mint/curve/vault/owners, applicable bank-bound Global/FeeConfig, exact native fees and curve arithmetic, physical reserve invariants, an exact terminal bank state and unchanged history fences. Reconstruction budgets remained 12 requests / four unique signatures, with the existing research freshness limit. Ordinary quality thresholds were unchanged.

Three passive captures produced 17 attempts: one PASS, seven FAIL_CONTINUITY, four FAIL_BUDGET, one FAIL_CONFIG and four captured FAIL_OTHER. The latter four are provider failures: a 429 response followed by three circuit-open rejections without HTTP requests. Historical statuses are preserved, with separate evidence-backed classifications. Fifty actual capture HTTP reads and nine separate forensic transaction reads were used. Attempted service calls are not silently counted as network requests.

| Requested question | Finding |
| --- | --- |
| Did a real live candidate PASS? | Yes: one standard simple-route sell candidate. |
| What prevented other PASSes? | Six direct transaction availability failures, one unproven native/physical reconstruction, four exhausted signature windows, one config invalidation, and four provider failures. |
| Did address indexing cause the four old rejects? | Missing index anchors were their immediate veto. Eventual consistency is directly evidenced for one; the other three lack retained history packets. A causal majority cannot be proven. |
| Does direct signature anchoring solve this safely? | Yes for an otherwise provable terminal state: the live PASS had no indexed anchor. It does not bypass missing successors, parity, current-bank equality or invalidation checks. |
| Which fee branches occur? | Ordinary protocol/creator fees and a protocol buyback split; three recovered historical fee rejects show native holder rewards. Other original rejection branches are not recoverable. |
| Can a narrow simple cohort be verified? | A complete live sell proof demonstrates feasibility. Complex routes remain excluded. |
| Do live buys match? | Two retained native buys pass strengthened integer and actual-transfer checks. Neither is a complete buy candidate PASS. |
| Do live sells match? | One retained sell passes exact integer, destination and trader-transfer checks; this is the complete candidate PASS. Other sampled sells remain unproven because of wallet-flow or instruction ambiguity. |
| Successful cost? | Six proof reads: one transaction, four histories, one account batch. Refresh rehearsal adds one batch, total seven. With N=1, mean/median/p90/max all equal the single observation. |
| Successful latency? | 353.2545 ms. Account state was 170.625 ms old at completion. N=1 is not a representative distribution. |
| What changed at refresh? | The batch arrived 110.563 ms after proof completion, at the same slot with identical account contents. Reserve, price and quote deltas were zero. The refresh was rejected because an intervening invalidation removed the receipt. |
| Ready for synchronized calibration? | One synchronized packet proves feasibility. The readiness gate remains false pending refresh invalidation handling and representative supported-cohort evidence. |

The original refresh error said “stable binding changed”; retained bytes prove the binding did not change. The service now reports receipt invalidation during refresh separately from an actual identity/config change. It still rejects the refresh. No permanent expiry threshold or disagreement bands were inferred from one point.

Machine reports: `analysis/live_candidate_proofs.json`, `live_continuity_lag.json`, `live_fee_routes.json`, `live_integer_parity.json`, `live_proof_gate.json`. Original capture packets remain in `live_execution_proofs_run1/2/3.json`. Database safety verification compares repeatable-read counts and trading controls with the prior baseline.

Final validation: 309 regression tests passed, Ruff passed, and strict mypy passed for 117 source files. Database counts and trading controls match the prior baseline; there are zero open positions and zero `runner-edge-prospective-v1` experiment rows.
