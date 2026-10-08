# Invalidation-scope ablation

The sole prospective pre-refresh SELL PASS was Ez6rCMBVjogDgaoSJ7Lw5Qts1q9NQ9dxyQQ7NWHQpump. Its refresh at slot 452707952 advanced two slots with unchanged reserves, quotes, identity/config binding, but two UNKNOWN_NATIVE_INSTRUCTION VENUE invalidations revoked trust.

The retained trigger signatures are:

- `4iFrddn1q1SJ2rf51Bv6dvGf8nekwjM7WQrtTVQuE6CJL9ATxHmAhiTiKUk9Dh7rpzqfW9V3tooxULaKJL4UEydd`
- `4Baif77Siwf1nV1dvDkVXeeV157gpy9c1hKARBYgRgxfo5KE2XfEsQ4qAYVHJ3trTjMAZR6uShotG8x4WbXGwBea`

Neither full executed transaction packet is present in the retained raw stream archive. The invalidation/log metadata cannot establish actual instruction names, complete accounts or writable privileges. Ability to write curve, vault, mint, Global, FeeConfig, creator binding and lifecycle is UNKNOWN for each. Unchanged sampled state does not prove absence of write reach or an intervening change. No retrospective transaction fetch was added.

## Experimental scoped design

Only a validated complete executed transaction envelope can bound write reach. Decode static signer/readonly header privileges and all loaded writable/readonly lookup addresses; unresolved lookup counts, invalid headers, failed/truncated envelopes or absent packets produce UNKNOWN. Include every protected curve/vault/mint/config/creator/lifecycle address. A writable intersection means MAY_WRITE, not demonstrated mutation. Another market binding cannot exempt a shared writable Global/FeeConfig/creator account.

If the complete writable envelope excludes all protected addresses, account/market modes can avoid collateral revocation. CPI cannot escalate writable privileges beyond the caller ([official CPI privilege rules](https://solana.com/docs/core/cpi)), which supports this bound; it does not supply missing transaction envelopes. If scope is UNKNOWN, all safe modes fall back conservatively to revocation. The research helper is not connected to production invalidation.

| Mode | Actual revocations (2 triggers) | Demonstrated actual false collateral | Demonstrated unsafe misses | Sole receipt safely preserved | Synthetic collateral revocations / unsafe misses |
|---|---:|---|---:|---|---|
| GLOBAL/VENUE | 2 | UNKNOWN | 0 demonstrated | no | 2 / 0 |
| ACCOUNT | 2 | UNKNOWN | 0 demonstrated | no | 0 / 0 |
| MARKET | 2 | UNKNOWN | 0 demonstrated | no | 0 / 0 |

The seven synthetic scope cases distinguish unrelated user writes / another curve with readonly shared config from writable candidate curve, Global, FeeConfig, creator/lifecycle and missing scope. Additional privilege tests cover loaded writable Global, unresolved lookup addresses and changed readonly-to-writable flags. Synthetic collateral counts establish design behavior, not empirical provider false-positive rates. Zero demonstrated unsafe misses in two unknown real triggers is not broad safety validation.

Policy D shadow-accepts the SELL by omitting unknown invalidation reach. This is KNOWN_UNPROVABLE_ACCEPTED, not a safely preserved proof. B/C and every safe scope mode remain rejected. No retained evidence proves these instructions actually could or could not mutate the target. The next missing evidence is their complete executed privilege envelopes plus relevant mutation-window closure; this task authorizes neither extra capture nor increased budgets.

Exact trigger metadata, scope verdicts and adversarial matrix are in [invalidation_scope_ablation.json](../analysis/invalidation_scope_ablation.json).
