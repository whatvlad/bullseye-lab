# Controlled proof-gate ablation

Completed offline against retained evidence. STRICT production code, strategy qualification, RPC/watch budgets and activation settings are unchanged. No new capture, provider calls, orders, calibration or runner activation occurred. Every evaluator verdict explicitly denies order, experiment and live authorization.

The supported prospective cohort yields STRICT **0**, B **0**, C **0**, D **1**. D admits unresolved evidence rather than demonstrating redundant safety. No relaxed execution gate is justified by this corpus.

## Method and policies

The evaluator uses true / false / unknown; absent evidence remains unknown. A historical stage PASS is not a full execution PASS. Fresh bank responses are re-decoded offline using the corrected production decoder and exact quote/accounting logic. No absent refresh, packet or historical account state is invented. B uses curve fence 1 before bank and curve fence 3 after bank, plus certified closure of all relevant mutation reach; this choice cannot itself prove vault closure.

A preserves exact supported reconstruction, price/fee parity, physical accounting, canonical identity/config, lifecycle, four fences, continuity, terminal/bank equality, final refresh and existing invalidation/refresh approval. B preserves that core with two fences and certified stream/mutation closure. C makes fences diagnostic only when certified ordered relevant mutation closure and terminal/bank equality replace their evidence. B/C remain fail-closed on unresolved protected mutation. D preserves supported route, exact anchor/reconstruction/parity/accounting, canonical identity/config, compatible lifecycle, valid atomic current state and a fresh compatible atomic refresh; it deliberately omits history/terminal-equality and unknown invalidation reach. D is a measurement policy, not a safe paper recommendation.

The natural/retained corpus has 47 cases: prospective 20, earlier 17, original SELL 1 and historical bad-state diagnostics 9. The last group retains transactions but lacks historical canonical banks/final refreshes; it is diagnostic, not reconstructed historical execution truth. Retained router/WSOL cases are rechecked, including unresolved intermediate-state/accounting limitations. Separately, 15 explicitly synthetic contracts exercise malformed identity/config, stale state, lifecycle/out-of-scope, multi-event, router/WSOL, absent refresh, changed binding, truncation, same-slot ordering, terminal mismatch and unknown shared-config mutation. Synthetic policy facts are not historical ground truth. Actual packet balance tampering and privilege-envelope tests supplement these contracts.

## Safety metrics

Natural/retained corpus:

| Policy | Cases | Shadow PASS | Additional PASS | Known unsafe accepted | Known unprovable accepted | Missing evidence accepted | Unchanged rejection |
|---|---:|---:|---:|---:|---:|---:|---:|
| STRICT | 47 | 0 | 0 | 0 | 0 | 0 | 47 |
| STREAM_PLUS_TWO_FENCES | 47 | 0 | 0 | 0 | 0 | 0 | 47 |
| STREAM_CURRENT_STATE | 47 | 0 | 0 | 0 | 0 | 0 | 47 |
| CURRENT_STATE_ONLY_RESEARCH | 47 | 2 | 2 | 0 | 2 | 0 | 45 |

Supported prospective cohort:

| Policy | Cases | Shadow PASS | Additional PASS | Known unsafe accepted | Known unprovable accepted | Missing evidence accepted | Unchanged rejection |
|---|---:|---:|---:|---:|---:|---:|---:|
| STRICT | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| STREAM_PLUS_TWO_FENCES | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| STREAM_CURRENT_STATE | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| CURRENT_STATE_ONLY_RESEARCH | 16 | 1 | 1 | 0 | 1 | 0 | 15 |

Synthetic contracts (separate, never added to natural counts):

| Policy | Cases | Shadow PASS | Additional PASS | Known unsafe accepted | Known unprovable accepted | Missing evidence accepted | Unchanged rejection |
|---|---:|---:|---:|---:|---:|---:|---:|
| STRICT | 15 | 1 | 0 | 0 | 0 | 0 | 14 |
| STREAM_PLUS_TWO_FENCES | 15 | 0 | 0 | 0 | 0 | 0 | 14 |
| STREAM_CURRENT_STATE | 15 | 0 | 0 | 0 | 0 | 0 | 14 |
| CURRENT_STATE_ONLY_RESEARCH | 15 | 5 | 4 | 0 | 4 | 0 | 10 |

ADDITIONAL_PASS compares to A. KNOWN_UNPROVABLE includes removed guards with unresolved safety, not demonstrated financial harm. MISSING_EVIDENCE_ACCEPTED tracks cases classified with missing required execution evidence; it does not mean that D's omitted historical evidence suddenly exists. UNCHANGED_SAFE_REJECTION means continuing to reject defective/unproven evidence, not certifying the market safe. Zero known-unsafe admissions is not a safety guarantee: adverse execution truth is largely unavailable. D's four additional synthetic admissions expose truncation, ordering, terminal mismatch and unknown mutation reach.

The original SELL mint F57hJHhuG6ryRYNPncoN34xR31pn9r9b3Pbi2odtEQ7v had a recorded pre-refresh PASS but a refresh failure: `stable binding changed; new proof required`. Its retained initial/fresh bank decodes now agree in binding, valid offsets and quote math (110.6 ms from decision). That does not reproduce or explain the old runtime/cache lineage failure. STRICT approval remains absent; D's retrospective admission is counted unprovable, not a complete live SELL PASS.

## Every prospective candidate

| Case | Mint | A | B | C | D | Difference / retained limitation |
|---|---|---|---|---|---|---|
| prospective_0 | Ez6rCMBVjogDgaoSJ7Lw5Qts1q9NQ9dxyQQ7NWHQpump | reject | reject | reject | shadow accept | D removes unknown concurrent mutation reach; bank/refresh agree, safety remains UNKNOWN. |
| prospective_1 | D5WSkqVV2EWydhVG87FTeJDZjGwuU53Pvyk43Pxtpump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_2 | A5n59HFgiLKqX6uLZQngZiJU7MKWYzgFFuY8xNPspump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_3 | 3goJ5ku2kMvPqngGj2H4MkrBiQ11nJRta7CS3SpQpump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_4 | 5eKa7UeQxhzxWJZjGyVwmYTGCecX6BvabTjcdYhJq8jd | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_5 | 58vp8HJvHZJJ4grZQiXNxS3WWpZHmkaJygwqMtBupump | reject | reject | reject | reject | No verdict difference. exact_reconstruction; exact_physical_accounting; missing exact_parity; missing canonical_identity_config; missing compatible_lifecycle_mode; missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_6 | 6xgq7auPCLLerxnZXcxYKriU5qbBh29UXDEHyzRYJTRN | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_7 | 5SQxaA1mcaUecT2QHoQLtWB9XQWFQ4n8ifn2czA6bDXE | reject | reject | reject | reject | No verdict difference. standard_supported_route; canonical_identity_config; missing exact_parity; missing compatible_lifecycle_mode; missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_8 | 9U55iP4HpqokKU7woVqvV5NWQ9RuBrMuN3iHs7bDpump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_9 | 8S3eeC7fri54DAgfne9EffHKp8yuh7nMEhACzg4apump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_10 | BocMmqqHwFpxd3paRer6uHJyosni658ksgSVTUwkpzvm | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_11 | CxsFik6cZCV83aKZtjP2TJWXwrFWFdHrfopoAeV988WX | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_12 | BK6JRoU7QCXRVT7xS3hVSe9UWMumBxo4c7Y17YNz1qw | reject | reject | reject | reject | No verdict difference. missing exact_anchor; missing exact_reconstruction; missing exact_parity; missing exact_physical_accounting; missing canonical_identity_config; missing compatible_lifecycle_mode; missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_13 | 3UWWiCgwEQk458oaDnEtx4uMeGzvz5hdWb9UVk55eMhH | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_14 | 76mYJijkX6X7fg1K98BZj52EHJQ1QDaEdQD8kVxipump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_15 | AWXXpESEecuCZ3GqMYrM2aj3pgDvg1Dy4atpfCQppump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_16 | 7bKrQ7UFrMyWshLE1vH4DMtQN7VKFf9qW7jBaRS4pump | reject | reject | reject | reject | No verdict difference. exact_reconstruction; exact_physical_accounting; missing exact_parity; missing canonical_identity_config; missing compatible_lifecycle_mode; missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_17 | 22ZnBvQioEsWCrBKzyH1uA4JJ7fJ1Vk8P9dDoPyyoweb | reject | reject | reject | reject | No verdict difference. exact_reconstruction; exact_physical_accounting; missing exact_parity; missing canonical_identity_config; missing compatible_lifecycle_mode; missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_18 | FunRidffE4gXaT2ucU4sEJ8owerc27mBNh3k4vHDpump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |
| prospective_19 | CPSSotDvqo9WhjpB7pB2FijXicsBLWTxCXfnNa4Cpump | reject | reject | reject | reject | No verdict difference. missing refresh_retained; missing refresh_identity_config; missing refresh_binding_compatible; missing refresh_fresh; missing current_state_consistent |

Exact failed/missing requirements for every policy and rechecked accounting/bank details are in [proof_gate_ablation.json](../analysis/proof_gate_ablation.json). B/C also lack certified relevant mutation-window closure. All 20 prospective stream certificates are incomplete; earlier observed trade-window certificates do not establish all-program mutation closure.

## Funnel and dominant blockers

The recorded supported funnel is reconstruction/parity 15/16, raw history closure 3/16, synchronized bank 9/16, pre-refresh proof 1/16, full proof 0/16. Among all 20 final dominant blockers: HISTORY_BOUNDARY 6, STATE_SYNC 5, unsupported route 4, invalidation 2, refresh 1, budget 1, provider 1. Missing final refresh for 19/20 censors downstream ablation; it is not evidence that 19 refreshes failed. Requirements overlap and cannot be summed as independent causal rejections.

Offline A requirement availability:

| Requirement | True / contradicted / unknown in 20 |
|---|---|
| standard_supported_route | 19 / 1 / 0 |
| exact_anchor | 19 / 0 / 1 |
| exact_reconstruction | 16 / 3 / 1 |
| exact_parity | 15 / 0 / 5 |
| exact_physical_accounting | 16 / 3 / 1 |
| canonical_identity_config | 15 / 1 / 4 |
| compatible_lifecycle_mode | 15 / 0 / 5 |
| refresh_retained | 1 / 0 / 19 |
| refresh_identity_config | 1 / 0 / 19 |
| refresh_binding_compatible | 1 / 0 / 19 |
| refresh_fresh | 1 / 0 / 19 |
| current_state_consistent | 1 / 0 / 19 |
| fence_1 | 17 / 0 / 3 |
| fence_2 | 15 / 0 / 5 |
| fence_3 | 4 / 5 / 11 |
| fence_4 | 4 / 5 / 11 |
| bounded_continuity | 3 / 6 / 11 |
| terminal_bank_equal | 9 / 6 / 5 |
| strict_invalidation_clear | 17 / 3 / 0 |
| strict_refresh_approved | 0 / 1 / 19 |

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
