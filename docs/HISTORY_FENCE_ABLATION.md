# Independent history-fence ablation

STRICT remains unchanged. The four fences are evaluated separately against retained prospective histories, not treated as a single rule. Candidate indices are zero-based.

| Fence | Uncertainty addressed | Received | Stage rejection / raw change | Unique changed case | Uniquely demonstrated unsafe execution |
|---|---|---:|---|---|---:|
| 1: curve discovery before bank | Initial bounded curve signature history, anchor/order availability | 17 | 0 immediate rejection | none | 0 |
| 2: vault discovery after initial bank receipt | Additional protected-vault activity, bounded history/signature budget | 15 | 1 budget rejection: case 3 | case 3 budget, not unsafe truth | 0 |
| 3: final curve history | Curve activity arriving during proof | 9 | 5 changed: 1,2,6,10,15 | case 10 | 0 |
| 4: final vault history | Vault activity arriving during proof | 9 | 5 changed: 1,2,6,13,15 | case 13 | 0 |

Fences 3/4 overlap in four cases, six distinct changed histories overall. Case 10 adds four successful rows and one failed row at fence 3 only. Case 13 adds four failed rows at fence 4 only. Raw equality therefore rejects a failed-only change in that case; it does not demonstrate unsafe protected state. Failed Solana transactions revert their state changes, while fees can still be charged ([official transaction semantics](https://solana.com/docs/core/transactions)). Failure rows still require reliable classification and complete successful mutation coverage before claiming redundancy.

Case 3's vault list contains five successful signatures including the anchor, exceeding the unchanged four-signature cap. Curve index-lag evidence does not erase that actual budget excess. Received fences 1/2 can return index-lagged lists without immediate rejection; terminal/bank and later history checks supply additional protection.

Removing only fence 3 would clear the history obstacle for case 10; removing only fence 4 would clear it for case 13. These are conditional pre-refresh differences, not full proof PASSes: both final refreshes are missing and other unresolved guards are not erased. Full additional PASS is zero for every single-fence removal. Detailed histories and signature changes appear in [history_fence_ablation.json](../analysis/history_fence_ablation.json).

## Replacement evidence

An atomic bank establishes one state snapshot. A compatible final refresh establishes fresher executable state, identity and fee inputs. They do not independently establish ordered continuity, missed round-trip mutations or absence of concurrent unknown config/creator writes. Part of history's freshness role overlaps with these snapshots, but its mutation-coverage role does not.

Current 20: zero complete observed stream windows. Earlier 17: two audited observed Pump trade windows, zero equivalent all-relevant protected mutation closures. No evidence justifies replacing a production fence in this task. B's before/after fences are curve 1/3; vault/config/creator coverage must come from its mandatory independent closure certificate. C requires that closure without individual fence requirements. Both currently reject every natural case.

Minimum future equivalent evidence must bind the exact anchor, relevant account/filter scope, ordered terminal state and bank/refresh boundary; cover loaded/CPI and shared config/creator reach; expose disconnect, overflow, ordering and retention gaps; and fail closed on unclassified mutation. An observed trade-only window is insufficient. This study does not increase budgets or activate that alternative.

## Five synchronization cases

| Case | Actual changed state | Matching packet timing / primary artifact | Final refresh | Safety under current-state relaxation |
|---|---|---|---|---|
| 8 | yes | after proof / STREAM_DELIVERY_LAG | absent | UNKNOWN |
| 9 | yes | after proof / STREAM_DELIVERY_LAG | absent | UNKNOWN |
| 11 | yes | after proof / STREAM_DELIVERY_LAG | absent | UNKNOWN |
| 14 | yes | after proof / STREAM_DELIVERY_LAG | absent | UNKNOWN |
| 19 | yes | during proof before bank receipt / INDEX_LAG | absent | UNKNOWN |

All exact bank-minus-terminal reserve deltas match retained POST_TRADE packets. Five real movements and five acquisition artifacts are overlapping counts. None is empirically shown to be an unsafe final current snapshot; none can be declared safe without its missing final refresh. Sequence/receipt evidence is in [proof_gate_ablation.json](../analysis/proof_gate_ablation.json).
