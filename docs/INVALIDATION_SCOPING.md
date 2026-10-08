# Invalidation scoping

The corrected provider uses event market bindings, canonical mint-to-curve derivation, the native invocation stack and cached account/vault identities. Live `logsSubscribe` does not expose transaction writable accounts or instruction data. Those are used only in bounded research reads. Missing transaction/instruction indices are null, never inferred from event ordinal.

| Trigger | Minimum safe scope | Trust invalidated |
|---|---|---|
| Unsupported instruction with decoded pool/curve/mint binding | POOL / MARKET | Reserves, identity and config unless IDL proves narrower writes |
| Silent self-CPI with proven native parent market | POOL / MARKET | Uncertain mutation retained; never silently ignored |
| Native program known, market unresolved | VENUE | Relevant dimensions |
| Truncated logs with program evidence | VENUE | Reserves |
| Truncation without program evidence | GLOBAL | All dimensions |
| Shared fee mutation with unproven venue | GLOBAL | Config only; observational reserves remain usable |
| Shared WebSocket disconnect | GLOBAL | Lost mutations across subscribed venues |
| Integer continuity break / multi-event ambiguity | MARKET | Reserve history; one coalesced repair |
| Requested RPC account failure | Cached affected markets | Reserves; identity is cleared only on binding failure |
| Owner/address/migration/config mismatch | Identified market or config venue | Proven affected dimensions |

Every tracker invalidation records reason, scope, program, signature, slot, known indices, affected markets, identity-known flag, repair-queued flag and dimensions. Original invalidation cause survives later consistent ticks. The bounded ledger and coalesced pending dictionary avoid unbounded in-memory growth; the passive run retains its full 39,594-record ledger.

The final capture has 19,616 active invalidations. 18,806 (95.87%) affect exactly one market. There are 0 global reserve invalidations and 18 deliberately retained global config-only invalidations. GLOBAL causes zero UNKNOWN trade observations; remaining UNKNOWN is attributed to MARKET/POOL/VENUE.

The pure-scope replay reproduces every held local status, with the same events, native mutation coverage and transaction order. It finds **zero UNKNOWN reduction attributable to scoping alone**. The old-helper versus new-helper comparison adds invocation-frame coverage and is not a pure scope comparison. No improved feed-reliability claim is made. The previous 3,962-event capture lacks native mutation frames and cannot be reconstructed exactly without additional chain acquisition.

Code: `providers/solana/invalidation.py`, `market_state.py`, `providers/solana/pump.py`; evidence: `analysis/invalidation_scope.json` and `analysis/replay_invalidation_scope.py`.
