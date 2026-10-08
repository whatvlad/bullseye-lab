# Cappuccinu price discrepancy

Position `19ac436f-d663-496b-bcc5-f969c27c4712`; mint `H1qib6bJJ2EUA61nwq8XuFfEZDq51HW9XKKey57Tpump`. Source: immutable 2026-10-01 07:27:25 UTC database export and [extracted evidence](../analysis/cappuccinu_price_evidence.json). Prices below are raw quote/token; times are UTC.

## What is established

| Evidence | Value |
|---|---|
| Actual paper entry fill | 2026-09-17 12:44:18.410081; `0.00009599807453395956` |
| Recorded observational peak | `0.000147795027115137`; +53.95624114% versus actual entry price |
| Longest receipt silence while open | 268.811314 seconds, 12:59:34.861084 to 13:04:03.672398 |
| Previously reported gap | 268.811291 seconds using ingestion timestamps; 23 microsecond difference from receipt definition |
| Last received feed tick before close | 13:20:22.870445; stream marginal reserve mark `0.00012280294748570764` |
| Stream reserves at that tick | Virtual quote 62,873,101,399; virtual token 511,983,650,932,462; real quote 32,873,101,399 |
| RPC execution snapshot | 13:20:23.105385; slot 447805104; virtual quote 32,470,589,188; virtual token 991,358,671,495,761 |
| RPC marginal reserve mark | `0.00003275362401279893`, 73.3283079% below the stream mark |
| Snapshot spacing | Last feed receipt to RPC observation: 0.234940 seconds; last feed receipt to fill: 0.451885 seconds |
| Simulated sell fill | 13:20:23.322330; `0.00003248672046829802`; stop-loss close |
| Recorded result | -20.56507668 USDT; -67.08297666% |

The 268.81-second gap was **not at the exit**. Fresh receipt does not prove fresh chain data: this provider's source timestamps were receipt estimates and no source slot was stored. Neighboring feed ticks also retain substantially higher reserve states around the RPC close; see the extracted near-exit ticks.

The fill ledger reconciles: entry cost 30.65617792 USDT; gross exit proceeds 10.28210005; exit fees 0.19099881; net proceeds 10.09110124; resulting loss -20.56507668. The observed peak ratio explains +53.96% mathematically, but does not prove that a sell of this position could have filled there.

## Cause assessment

The immediate numerical cause of the recorded loss is the much lower RPC reserve state used by the paper sell. The immediate cause of the apparent MFE-to-loss contradiction is comparing an observational stream peak with a simulated RPC-state, impacted, fee-inclusive outcome.

| Candidate explanation | Finding |
|---|---|
| Real market collapse | Possible; RPC reserves imply a large decline in curve value. Not proven without independently timed account/transaction evidence. |
| Stale trade feed | Long silence is proven earlier. At exit receipt was recent, but buffered/lagged vendor events remain possible because actual chain event time is unknown. |
| Missing subscription data | Possible during silence; no per-position complete subscription/acknowledgment history proves the cause. Absence of events could also mean no trades. |
| RPC/reserve-state disagreement | Proven numerically for nearby receipts and the same market. The two virtual reserve products are approximately the same curve invariant, but states differ drastically. This supports different states of the curve; it does not identify which was contemporaneous. |
| Execution-model mismatch | Proven in the old peak/stop/valuation comparisons. It explains why MFE was not a net executable return, but does not itself explain the 73.33% reserve-mark gap. |
| Average trade quote methodology | Last average transaction price is only about 1.1% above its reserve mark. The discrepancy persists when comparing marginal reserve marks, so average-versus-marginal methodology is insufficient. |
| Paper-fill costs/assumptions | Stored exit impact 31.65 bps and adverse slippage 50 bps explain the small RPC-mark-to-fill difference. Fees and SOL/currency conversion cannot explain a 73.33% reserve discrepancy. Fee fidelity is still conditional. |
| Erroneous, cached or lagged RPC state / wrong decoding | Cannot exclude from stored evidence. Raw account-response bytes, endpoint identity, independent slot freshness and synchronized stream slots were not preserved in the legacy fill. |

**Root causality cannot be proven.** Evidence supports a material stream/RPC state discrepancy and an execution-evidence comparison problem. It does not support declaring a rug, creator manipulation, a proven contemporaneous collapse, or attributing the loss solely to the earlier feed gap.

Old PnL is trustworthy as a record of what the simulator booked, with reconciled arithmetic. It is not independently trustworthy as executable market PnL or an unbiased strategy-performance label. Old observed MFE/MAE must remain separate from execution outcomes. Historical rows were not rewritten.
