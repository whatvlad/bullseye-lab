# Stream provider comparison — 2 October 2026

Update: the user subsequently enabled Alchemy PAYG. Mainnet Yellowstone now
delivers filtered executed packets. See [the working filtered pilot](FILTERED_STREAM_PILOT.md)
for current access, counts, costs and remaining blockers. The comparison below
records the earlier probe and does not describe current Alchemy entitlement.

Configured endpoints are Alchemy HTTP, Helius WebSocket and public Solana exit
HTTP. No gRPC endpoint/token or provider plan is explicitly configured. Credentials
were never printed or persisted into reports. No account purchase, plan upgrade,
dashboard change or service activation was performed.

Helius transactionSubscribe on the configured current mainnet endpoint returned
JSON-RPC -32600, with message terms indicating unavailable on this plan. It supplies
no full packet under the current credential. Ordinary logs/slots/config account
subscriptions work. Alchemy's documented mainnet streaming endpoint, authenticated
with the existing RPC app key as x-token, returned gRPC UNIMPLEMENTED for Ping and
the actual filtered Subscribe. This establishes no usable stream in this probe;
it does not identify the account plan, authentication entitlement or exclusive
cause. The existing HTTP key is not proof that gRPC service is enabled.

| Option | Transaction completeness/order | Accounts and reconnect | Access/cost | Practical complexity |
| --- | --- | --- | --- | --- |
| Current Helius standard WSS | Logs/signature/slot only; lacks inner instructions/balances/index | Individual account subscriptions; no local replay certification | Working credential; billed usage unknown | Low; insufficient proof source |
| Helius enhanced WSS | Full executed message/meta, logs, balances, optional transactionIndex | Account subscriptions; application gap/replay validation still needed | Developer minimum, $49/month; current account rejects it | Low/medium; implemented packet adapter, no closed-window certificate |
| Helius LaserStream gRPC | Executed transactions/full metadata and ordering | Geyser accounts/slots; documented replay/resume support | Business mainnet minimum $499/month; not configured/tested | Medium; protobuf transport and rigorous delivery barriers |
| Alchemy Yellowstone | Executed transactions/meta and block index | Account/slot/block updates and documented gap filling | Quickstart says PAYG/Enterprise; published $75/TB; existing probe UNIMPLEMENTED | Medium; resolve endpoint/access before buying anything |
| QuickNode Yellowstone | Full transaction/account/slot/block API | Published fromSlot replay up to 3,000 slots | Not configured; Scale $499/month, 10 credits/0.1 MB | Medium; new provider setup, no demonstrated need to switch |
| Public Solana WSS/RPC | logsSubscribe plus retrospective getTransaction | Per-account subscription; blockSubscribe is node-dependent | No project stream entitlement established | Low; preserves measured acquisition bottleneck |

These are capabilities, not measured provider latency rankings. The pilot has no
full-stream transaction latency sample. Packet receipt time is exposed; provider
delivery latency requires an independent execution timestamp and clock model.

Helius's current documentation describes full transaction filtering, metadata and
transactionIndex. Its April 2026 access matrix enables enhanced WSS on Developer
and mainnet gRPC on Business, and meters streams at 20 credits/MB. The actual
project's credit allowance, overage policy and billed bytes are unknown.
Sources: [transactionSubscribe](https://www.helius.dev/docs/api-reference/rpc/websocket/transactionsubscribe),
[access and metering update](https://www.helius.dev/blog/laserstream-websockets),
[pricing](https://www.helius.dev/pricing),
[gRPC guide](https://www.helius.dev/docs/laserstream/grpc).

Alchemy's API exposes transaction index/full metadata, accounts and slots. Its
quickstart and pricing restrict Yellowstone to PAYG/Enterprise, while its marketing
page says no plan prerequisite. Treat that contradiction as unresolved for this
account. The $75/TB rate is published, not a verified billing agreement here.
Sources: [quickstart](https://www.alchemy.com/docs/reference/yellowstone-grpc-quickstart),
[transaction response](https://www.alchemy.com/docs/reference/yellowstone-grpc-subscribe-transactions),
[overview](https://www.alchemy.com/docs/reference/yellowstone-grpc-overview),
[pricing](https://www.alchemy.com/pricing),
[marketing rate/access statement](https://www.alchemy.com/solana-grpc).

QuickNode publishes Geyser streaming, Scale/Business inclusion, byte-credit metering
and recent-slot replay. Those provider guarantees still require local reconciliation.
Sources: [protocol overview](https://www.quicknode.com/docs/solana/solana-grpc/overview),
[June 2026 plans and replay](https://www.quicknode.com/blog/solana-grpc-is-now-included-with-scale-and-business-plans).
The upstream [Yellowstone schema](https://github.com/rpcpool/yellowstone-grpc/blob/master/yellowstone-grpc-proto/proto/geyser.proto)
distinguishes executed metadata streams from pre-execution/deshred streams.
Pre-execution streams alone cannot prove fees, balances or reserve outcomes.

Minimum next infrastructure is a working executed-transaction stream with account
mutations, ordering and verifiable replay/window closure, plus one final atomic
RPC refresh. Resolve the existing Alchemy endpoint/entitlement first. If it is
unavailable, Helius Developer WSS is the minimum documented paid option among
the configured vendors for full packet capture, but does not by itself establish
four-fence equivalence. Mainnet gRPC may be appropriate for verified recovery;
the $499 tier is not justified merely by this failed short log pilot. No upgrade
is recommended as an automatic action. Obtain working access and a bounded
full-packet benchmark before selecting a plan or forecasting full-stream cost.
