# Proof to refresh recovery

The first live sell PASS's receipt was removed by `PassiveCandidateProof.native_transaction`, which detected a Pump.fun venue/config generation change and called global `invalidate("CONFIG_UPDATE_OR_UNKNOWN_CONFIG_MUTATION")`. That incremented generation and cleared receipts, stable bindings and config cache. The refresh compared against the now-empty cache and incorrectly described its failure as a changed stable binding.

Both retained account batches have identical contents and slot 452440138. The refresh arrived 110.563 ms after proof completion. The old packet does not retain a timestamped link to the exact native transaction/frame that caused invalidation. Its exact triggering signature and whether that frame represented a known config update or unresolved mutation cannot be proven. Identical bytes alone do not resolve that uncertainty.

Each proof now tracks RESERVE_STATE, IDENTITY, CONFIG, CONTINUITY, FEE_ROUTE, LIFECYCLE, MODE and STREAM_COVERAGE separately. Notifications record timestamp, source signature/slot, scope, dimensions and incompatible-mutation status. A revoked active receipt retains its evidence lineage, permitting bounded current-state revalidation without treating cache presence as evidence.

| Dimension | One atomic refresh can restore it? | Boundary |
| --- | --- | --- |
| RESERVE_STATE | Yes | Current bank fields and physical relationships, not intermediate history. |
| IDENTITY | Yes | Current canonical mint/curve/vault/PDA/owners/token semantics. |
| CONFIG | Yes | Current canonical config owners, schema, binding and content hashes. |
| FEE_ROUTE | Yes for the unchanged supported simple route | Current route flags, creator/config inputs and integer quotes. Changed stable binding requires a new native proof. |
| LIFECYCLE / MODE | Compatible current state can be validated | Known incompatible migration/completion/mode evidence remains blocked. |
| CONTINUITY | No | Requires a new bounded native transaction proof. |
| STREAM_COVERAGE | No | A current bank snapshot cannot recover an unobserved interval. A new bounded proof establishes only its own stated coverage. |

Refresh never advances `continuity_proven_through_slot`. It does not prove absence of unseen intermediate mutations or repair old observations. A notification received during a batch cannot be overwritten when its source slot is absent or is at/after that bank. Known earlier-source notifications may be covered by the fresh bank's independent current checks; historical dimensions remain separate.

Outcomes distinguish `FRESH_STATE_REVALIDATED`, `PROOF_STALE_BUT_CURRENT_STATE_VALID`, `STILL_BLOCKED_BY_UNPROVEN_CONTINUITY`, `CURRENT_STATE_REVALIDATION_PENDING` and `INCOMPATIBLE_MUTATION_BLOCKED`. `execution_approved` requires every execution dimension, freshness and compatible lifecycle. It is a passive research verdict; no order path was activated. An approved dictionary does not outlive later invalidation or downstream gates.

Replaying the first real packet under a known CONFIG-only invalidation restores execution dimensions if unchanged. Replaying its actual coarse UNKNOWN notification conservatively leaves continuity/coverage blocked while restoring independently proven current dimensions. This is not a retroactive approval of the historical refresh.

Regression coverage includes reserve, identity and config recovery; lost continuity/coverage; incompatible lifecycle; expiration; in-flight invalidation; and both interpretations of the original retained packet. Machine evidence: `analysis/proof_refresh_recovery.json`.
