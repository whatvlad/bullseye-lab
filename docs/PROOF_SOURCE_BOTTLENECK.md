# Proof source bottleneck

The existing log subscription sees the native event before candidate qualification.
It supplies signature, slot and log/event payload, but no raw message, inner
instructions, SOL/token balance changes or transaction index. Rolling features and
arithmetic continuity are local. The expensive physical, canonical and fee proof
starts after the existing aggressive strategy makes the market a serious candidate.

| Request | Purpose after qualification | Stream replacement requirement |
| --- | --- | --- |
| Native getTransaction | Full anchor/successor instructions, metadata, transfer/rent/fee and physical reserve proof | Already received compatible full transaction packet; local reuse is implemented |
| Curve history before | Discover relevant successors and bound anchor-to-bank sequence | Complete closed mutation sequence covering curve, not just Pump trades |
| Account bank | Atomic mint/curve/vault/Global/FeeConfig/sharing accounts, canonical ownership, mode/lifecycle, config and current reserves | Retained as one fresh atomic read; independent account notifications are not equivalent |
| Vault history before | Discover vault mutations omitted by curve-only history | Complete vault write/transaction coverage, including non-Pump token/System mutations |
| Curve history after | Detect history movement during bank/parity work | Sealed slot/bank boundary and delivery reconciliation with no missing curve writes |
| Vault history after | Detect vault changes during proof | Equivalent synchronized vault mutation boundary |
| Execution refresh | Revalidate current executable reserve/identity/config immediately before hypothetical execution | Mandatory fresh atomic read even with perfect historical stream |

The first and successor transaction reads, four fences, bank and refresh all use
the unchanged bounded policy: 12 reads, four signatures, 12 seconds; availability
probe count remains three. No history window, retry count or strategy threshold
was increased. Costs overlap: a single bank read covers identity and config roles.

The stored 74 failures group as follows:

| Failure site | Count | What prospective capture could change |
| --- | ---: | --- |
| Anchor transaction unavailable | 25 | A complete already captured packet avoids the null RPC read; it does not guarantee later proof success |
| getTransaction RPC response error | 2 | Compatible streamed metadata avoids that method; code -32015 alone does not establish provider outage or packet compatibility |
| Signature window/boundary exhausted | 8 | A certified rolling mutation proof could replace discovery; current caps/fences cannot simply be removed |
| Synchronization | 3 | Ordering and delivery barriers may improve it; fresh account state can still move |
| Native/physical reconstruction unproven | 10 | Same incomplete or semantically unexplained inputs still fail; transport change alone is not a demonstrated fix |
| Wallet/rent transfer ambiguity | 9 | Requires understanding all transfers/refunds; preserve rejection |
| Unsupported fee route | 14 | Deliberate exclusion, not a source bottleneck |
| Integer curve parity mismatch | 2 | Semantic mismatch remains; preserve rejection |
| Invalidation during proof | 1 | Requires independently restored trust; do not suppress invalidation |

27 failures directly target transaction acquisition, eight target bounded indexed
discovery and three target bank synchronization. **Zero failures have been causally
proven to be exclusively caused by retrospective acquisition.** The actual number
is unknown. These 38 failure sites are conditional improvement targets, not 38
future PASSes. Per-candidate classifications are in
analysis/retrospective_vs_stream.json, including every stored reason and signature.

The new provider probe found no usable configured full transaction subscription.
The paired pilot retained native RPC reconstruction and reproduced one physical
reconstruction failure in both paths. Full source replacement remains unvalidated.
