import json
from pathlib import Path
R=Path('C:/Bullseye')
a=json.loads((R/'analysis/proof_gate_ablation.json').read_text())
pol=list(a['policies'])
def table(counts):
 s='| Policy | Cases | Shadow PASS | Additional PASS | Known unsafe accepted | Known unprovable accepted | Missing evidence accepted | Unchanged rejection |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
 for p in pol:
  c=counts[p]
  s+='| '+p+' | '+' | '.join(str(c[k]) for k in ['cases','SHADOW_PASS','ADDITIONAL_PASS','KNOWN_UNSAFE_ACCEPTED','KNOWN_UNPROVABLE_ACCEPTED','MISSING_EVIDENCE_ACCEPTED','UNCHANGED_SAFE_REJECTION'])+' |\n'
 return s
cases='| Case | Mint | A | B | C | D | Difference / retained limitation |\n|---|---|---|---|---|---|---|\n'
for c in a['prospective_20']['cases']:
 reason='D removes unknown concurrent mutation reach; bank/refresh agree, safety remains UNKNOWN.' if c['id']=='prospective_0' else 'No verdict difference. '+('; '.join(c['policies'][pol[3]]['contradicted_requirements']+['missing '+k for k in c['policies'][pol[3]]['missing_evidence']]))
 cases+='| '+c['id']+' | '+c['mint']+' | '+' | '.join('shadow accept' if c['policies'][p]['shadow_pass'] else 'reject' for p in pol)+' | '+reason+' |\n'
funnel='| Requirement | True / contradicted / unknown in 20 |\n|---|---|\n'
for x in a['prospective_policy_funnels']['STRICT']:
 funnel+=f"| {x['requirement']} | {x['demonstrated_true']} / {x['contradicted']} / {x['missing_unknown']} |\n"
proof='''# Controlled proof-gate ablation

Completed offline against retained evidence. STRICT production code, strategy qualification, RPC/watch budgets and activation settings are unchanged. No new capture, provider calls, orders, calibration or runner activation occurred. Every evaluator verdict explicitly denies order, experiment and live authorization.

The supported prospective cohort yields STRICT **0**, B **0**, C **0**, D **1**. D admits unresolved evidence rather than demonstrating redundant safety. No relaxed execution gate is justified by this corpus.

## Method and policies

The evaluator uses true / false / unknown; absent evidence remains unknown. A historical stage PASS is not a full execution PASS. Fresh bank responses are re-decoded offline using the corrected production decoder and exact quote/accounting logic. No absent refresh, packet or historical account state is invented. B uses curve fence 1 before bank and curve fence 3 after bank, plus certified closure of all relevant mutation reach; this choice cannot itself prove vault closure.

A preserves exact supported reconstruction, price/fee parity, physical accounting, canonical identity/config, lifecycle, four fences, continuity, terminal/bank equality, final refresh and existing invalidation/refresh approval. B preserves that core with two fences and certified stream/mutation closure. C makes fences diagnostic only when certified ordered relevant mutation closure and terminal/bank equality replace their evidence. B/C remain fail-closed on unresolved protected mutation. D preserves supported route, exact anchor/reconstruction/parity/accounting, canonical identity/config, compatible lifecycle, valid atomic current state and a fresh compatible atomic refresh; it deliberately omits history/terminal-equality and unknown invalidation reach. D is a measurement policy, not a safe paper recommendation.

The natural/retained corpus has 47 cases: prospective 20, earlier 17, original SELL 1 and historical bad-state diagnostics 9. The last group retains transactions but lacks historical canonical banks/final refreshes; it is diagnostic, not reconstructed historical execution truth. Retained router/WSOL cases are rechecked, including unresolved intermediate-state/accounting limitations. Separately, 15 explicitly synthetic contracts exercise malformed identity/config, stale state, lifecycle/out-of-scope, multi-event, router/WSOL, absent refresh, changed binding, truncation, same-slot ordering, terminal mismatch and unknown shared-config mutation. Synthetic policy facts are not historical ground truth. Actual packet balance tampering and privilege-envelope tests supplement these contracts.

## Safety metrics

Natural/retained corpus:

'''+table(a['natural_corpus_counts'])+'''
Supported prospective cohort:

'''+table(a['supported_16']['counts'])+'''
Synthetic contracts (separate, never added to natural counts):

'''+table(a['synthetic_contract_counts'])+'''
ADDITIONAL_PASS compares to A. KNOWN_UNPROVABLE includes removed guards with unresolved safety, not demonstrated financial harm. MISSING_EVIDENCE_ACCEPTED tracks cases classified with missing required execution evidence; it does not mean that D's omitted historical evidence suddenly exists. UNCHANGED_SAFE_REJECTION means continuing to reject defective/unproven evidence, not certifying the market safe. Zero known-unsafe admissions is not a safety guarantee: adverse execution truth is largely unavailable. D's four additional synthetic admissions expose truncation, ordering, terminal mismatch and unknown mutation reach.

The original SELL mint F57hJHhuG6ryRYNPncoN34xR31pn9r9b3Pbi2odtEQ7v had a recorded pre-refresh PASS but a refresh failure: `stable binding changed; new proof required`. Its retained initial/fresh bank decodes now agree in binding, valid offsets and quote math (110.6 ms from decision). That does not reproduce or explain the old runtime/cache lineage failure. STRICT approval remains absent; D's retrospective admission is counted unprovable, not a complete live SELL PASS.

## Every prospective candidate

'''+cases+'''
Exact failed/missing requirements for every policy and rechecked accounting/bank details are in [proof_gate_ablation.json](../analysis/proof_gate_ablation.json). B/C also lack certified relevant mutation-window closure. All 20 prospective stream certificates are incomplete; earlier observed trade-window certificates do not establish all-program mutation closure.

## Funnel and dominant blockers

The recorded supported funnel is reconstruction/parity 15/16, raw history closure 3/16, synchronized bank 9/16, pre-refresh proof 1/16, full proof 0/16. Among all 20 final dominant blockers: HISTORY_BOUNDARY 6, STATE_SYNC 5, unsupported route 4, invalidation 2, refresh 1, budget 1, provider 1. Missing final refresh for 19/20 censors downstream ablation; it is not evidence that 19 refreshes failed. Requirements overlap and cannot be summed as independent causal rejections.

Offline A requirement availability:

'''+funnel+'''
## State synchronization

All five bank-minus-terminal deltas match actual captured later POST_TRADE state. Cases 8, 9, 11 and 14 delivered the matching packet after proof completion: primary STREAM_DELIVERY_LAG. Case 19 had it available during proof, before bank receipt: primary INDEX_LAG. All five also represent REAL_STATE_MOVEMENT; acquisition artifacts and actual movement overlap. Their transaction ordering and exact reserve deltas are retained in the JSON. No separate missing-transaction or same-slot ambiguity cause is needed for these five matched deltas. No final refresh exists for any of the five, so how many would be unsafe under D is UNKNOWN; all five remain rejected. A valid newer bank can be useful, but relaxing equality alone cannot establish safe final execution evidence.

## Twelve readiness answers

1. HISTORY_BOUNDARY (6) and STATE_SYNC (5) dominate the recorded final rejections; missing refresh censors 19 counterfactual full outcomes.
2. No natural case demonstrates a uniquely caught unsafe final execution. Exact accounting/identity/refresh checks reject adversarial defects; D uniquely admits four unprovable synthetic cases. Those tests establish guard behavior, not historical harm.
3. All four fences are not proven necessary, but this corpus does not justify removing any production check.
4. Certified ordered relevant mutation-window evidence could replace historical checks. No retained case has the required equivalent closure certificate.
5. Of 16 supported candidates: B 0, C 0, D 1; STRICT 0.
6. D accepts one prospective and one older unprovable case, plus four additional synthetic unprovable cases. No known-unsafe admission is demonstrated; safety is not proven.
7. All five STATE_SYNC cases reflect actual changed state.
8. All five also have acquisition artifacts: four delivery lag, one index lag. These are overlapping classifications.
9. VENUE invalidation can be over-broad when a complete writable envelope excludes every protected address. For these actual two triggers, collateral reach is UNKNOWN.
10. Scoped invalidation cannot safely preserve the sole proof using retained evidence; both trigger packets are absent.
11. Minimum evidence preserves canonical/config/lifecycle checks, exact math and physical accounting, fresh executable quotes, final atomic refresh, fail-closed mutation reach and bounded history closure or independently certified equivalent closure.
12. Offline/shadow measurement is possible; a relaxed PAPER execution experiment is not ready. No gate is activated; runner/calibration remain BLOCKED and live disabled.

See [history fence analysis](HISTORY_FENCE_ABLATION.md), [invalidation analysis](INVALIDATION_SCOPE_ABLATION.md), [minimum paper evidence](MINIMUM_SAFE_PAPER_GATE.md) and [completion gate](../analysis/ablation_gate.json).
'''
(R/'docs/PROOF_GATE_ABLATION.md').write_text(proof,encoding='utf-8')
history='''# Independent history-fence ablation

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
'''
(R/'docs/HISTORY_FENCE_ABLATION.md').write_text(history,encoding='utf-8')
inv='''# Invalidation-scope ablation

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
'''
(R/'docs/INVALIDATION_SCOPE_ABLATION.md').write_text(inv,encoding='utf-8')
minimum='''# Proposed minimum safe PAPER proof evidence

Status: **PROPOSED_NOT_ACTIVATED**. Offline/shadow policy comparison may continue; a relaxed PAPER execution experiment is not ready. Runner and calibration remain BLOCKED. Live trading and all order authorization remain disabled.

Minimum evidence must preserve:

1. Verified canonical mint/curve/vault/program/PDA/config/creator binding, supported standard Pump.fun simple SOL route, compatible completion/migration/lifecycle/mode at bank and refresh.
2. Exact anchor instruction/event reconstruction, reserve/executable price and fee parity, with every protected token/SOL movement explained. Router residuals, unresolved WSOL intermediates and multi-event ambiguity remain rejected.
3. A coherent atomic bank and mandatory fresh final atomic execution refresh. Recompute executable buy/sell outcomes, fees, impact/slippage from that state; bind the evidence to identity/config/lifecycle. Historical stage PASS cannot replace a refresh.
4. Fail-closed unknown protected/config/creator mutation reach during proof/refresh. Scope exemptions require a complete verified writable envelope excluding all protected accounts; missing packets remain conservative.
5. Bounded ordered mutation continuity terminating at the atomic bank, or independently certified equivalent relevant stream closure. Keep the existing STRICT four-fence fallback until the replacement is empirically validated.

No check removal is empirically justified here. B/C lack certified closure. D accepts unprovable cases and is not recommended as the minimum safe policy. Atomic snapshots can supply current prices but cannot alone establish unknown concurrent mutation safety. The four-fence control remains unchanged, even though universal necessity of every fence is not proven.

Remaining blockers: 19 prospective final refreshes absent, no complete current stream-window certificates, no all-relevant mutation closure certificates, two sole-SELL invalidation packets absent, and no complete safe natural prospective proof. The older SELL's recorded cache/binding refresh failure is also not explainable from retained bank responses alone.

A future readiness review needs retained full mutation privilege evidence, certified bounded ordering/coverage and a complete canonical/accounting/current refresh proof on naturally qualified standard candidates. It must demonstrate no unsafe/unprovable admissions before simplifying history or scope. Nothing here lowers strategy qualification, increases RPC/watch budgets, configures disagreement bands, starts calibration or authorizes a runner experiment.

Machine proposal: [minimum_safe_paper_gate.json](../analysis/minimum_safe_paper_gate.json). Completion and unchanged-code verification: [ablation_gate.json](../analysis/ablation_gate.json).
'''
(R/'docs/MINIMUM_SAFE_PAPER_GATE.md').write_text(minimum,encoding='utf-8')
