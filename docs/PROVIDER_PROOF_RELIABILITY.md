# Provider reliability during proof

The report separates transport/capacity failures, transaction availability, capture budget, proof timing and proof-evidence failures. None is a strategy PnL outcome.

HTTP success includes JSON-RPC success with a null transaction. That does not mean usable transaction evidence was available. HTTP 429 rate uses actual HTTP calls as its denominator. Circuit-open rate uses proof attempts; no request is charged for a preflight circuit rejection. Successful transaction poll times are upper bounds on availability, while unsuccessful bounded probes censor the observation. Null confirmed responses alone cannot establish address-index lag as their mechanism.

Combined observed results: 239 HTTP requests, 100% HTTP transport success, 237/239 (99.16%) JSON-RPC result success, zero HTTP 429s and zero circuit-open proof attempts. Two `rpc_-32015` replies are RPC response errors, not HTTP outages. Among 74 failed proofs, 25 transaction availability failures plus two RPC errors account for 36.49%; proof-evidence failures account for 63.51%. Availability and RPC errors are not strategy failures.

The 47 successful transaction availability probes had observed upper bounds of mean 358.581 ms, median 261.759 ms, p90 577.859 ms and max 1,267.786 ms from native receipt. These are polling observations, not exact backend indexing times. One collector validation error ended the first episode; one WebSocket transport disconnect ended the corrected episode. These are episode-level failures, outside the proof-failure denominator. Stream termination invalidates STREAM_COVERAGE; a reserve batch cannot restore it. Continuous reconnect/recovery was not demonstrated by this bounded collector.

Address-history window exhaustion is a bounded-evidence failure, distinct from provider outage. Instruction ambiguity, fee-route exclusion, unexplained wallet transfers, moved history fences and invalidation during proof also remain evidence failures. Outcomes and all denominators appear in `analysis/provider_proof_reliability.json`.

| Read | Uncertainty resolved | Optimization assessment |
| --- | --- | --- |
| Known-signature transaction | Native event/slot/instruction, actual transfers and physical pre/post state | Fetch once; reuse it when indexed. Null probes remain bounded. |
| Curve history before bank | Bounded successor discovery and curve-write boundary | Cannot be cached across active candidates. |
| Atomic account batch | Current identity, reserves, config, route and lifecycle/mode | Already batches seven canonical addresses in one request. Config decoding is cached by hash; live evidence still read. |
| Vault history before fence | Vault-specific changes outside curve writes | Curve history does not establish equivalent vault coverage. |
| Curve history after bank | Detect movement across proof reads | Retained; exact terminal equality is not complete intermediate-history evidence. |
| Vault history after bank | Detect vault fence movement | Retained for the same reason. |
| Refresh account batch | Current execution state and dimension-specific revalidation | One batch; no transaction/history enrichment unless a new proof is required. |

No history fence was removed without evidence. Direct anchoring eliminates duplicate anchor lookup and fetching predecessors merely because four signatures are allowed. An HTTP batch of histories would still contain separate logical reads and would not automatically reduce provider billing or proof uncertainty. Regression tests require a single anchor fetch, retain four fences and reject movement/missing state.
