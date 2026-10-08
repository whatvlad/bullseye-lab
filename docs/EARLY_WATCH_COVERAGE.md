# Early watch coverage before proof — 2026-10-02

Runner and synchronized calibration remain **BLOCKED**. No orders, wallet enrichment,
database mutations, strategy threshold edits, or proof-policy changes were made.
Alchemy PAYG Yellowstone was used with dynamic standard/non-Mayhem SOL account filters.
The paired run used 91 of the existing 96 RPC reads. The proof retains its 12-read
per-proof limit, four history fences, native/integer parity, and mandatory final atomic
execution refresh. Retrospective and stream-first proofs ran sequentially, so their
bank snapshots differ; this is not a randomized causal comparison.

## Implementation

`early_watch.py` records DISCOVERED → CHEAP_FILTERED → EARLY_WATCH →
SERIOUS_CANDIDATE → PROOF_PENDING, with REJECTED for exclusions/removal. Admission is
an observed standard Pump creation with supported SOL quote, derived curve agreement,
non-Mayhem, no cashback and no multiple-trade ambiguity. It does not change serious
candidate qualification. Mint/curve/both token-program vault PDAs are derived locally;
execution identity remains the existing independent proof's responsibility.

Full packet filtering starts at admission. WATCH_START/ACTIVE/COOLDOWN/REMOVED preserve
temporary deterioration through a five-second grace; thirty seconds of inactivity
starts cooldown. The existing 120-second hard retention/watch horizon is unchanged.
These are bounded research settings, not profitable strategy thresholds. Migration,
completion, unsupported fees, Mayhem and ambiguous transactions remove eligibility.
Hard exclusions are tombstoned so a later cheap trade cannot restore research eligibility.
Filter requests only change when the account set changes. No global Pump transaction
or global account subscription is used. Account packets invalidate watched config
trust but never replace the final atomic bank read.

## Decoder forensics and repair

The old pilot's **98 raw rejects were not archived**. Their exact causes and fixable
fraction cannot be proven retrospectively. They must not be relabeled as a diagnosed
98/98 adapter defect.

The new capacity-8 capture retained 234 complete protobufs: the original decoder accepted
110 and rejected **124** because `Message.config` was present. Every one of those 124
verified cryptographically against the V1 signed-byte layout; none verified as a
reconstructed V0/legacy message. The adapter had an explicit unsupported-V1 guard.
This was a correct fail-closed format limitation, repairable at the adapter boundary.

The repair reconstructs the signed V1 bytes and verifies every signature, checks key,
header, instruction, lookup and size constraints, preserves version **1** and config
fields, and converts complete execution metadata into the existing proof shape. It
does not relabel V1 as V0 or synthesize execution state. Signature/config/instruction
damage, forbidden lookups and missing metadata remain rejected. Serialization follows
the [SIMD-0385 specification](https://raw.githubusercontent.com/solana-foundation/solana-improvement-documents/main/proposals/0385-transaction-v1.md);
the specification page's status is not used to infer mainnet activation. Signed retained
packets are the evidence here.

Offline replay of capacity 8 recovers **96 usable trades + 28 non-trade executions**
from those 124 rejects: **100% repairable format exclusions in this new sample**, not
100% of the historical 98. Capacity 16 had 238 such format exclusions before repair;
post-repair replay yields 400 usable, 89 non-trade and one multi-event ambiguity out
of 490 packets. The live repaired capacity-32 capture has **4,334 packets, 1,286
usable trades, 3,048 non-trade executions, zero malformed/adapter rejects**.

NON_TRADE_EXECUTION is distinct from decoder loss: representative packets reference
watched accounts and the Pump program key but execute a different quote/read program
without a Pump TradeEvent. Account-key filters do not imply program invocation.
Their full packets are archived; they are not converted into invented trades. Multi-event
ambiguity stays excluded. No transaction reconstruction RPC is spent on these packets.

Every retained packet is classified and hashed in `early_watch_{8,16,32}_decoder_forensics.json`.
The complete requested rejection catalog, including zero counts, is in
`early_watch_summary.json`. UNSUPPORTED_TX_VERSION, MISSING_META, ACCOUNT_KEY_RESOLUTION,
LOOKUP_TABLE_ERROR, INNER_INSTRUCTION_PARSE, BALANCE_SCHEMA, PROGRAM_FILTER_MISMATCH,
MALFORMED_PACKET, ADAPTER_BUG, OTHER and UNKNOWN are all zero in the repaired 32 capture.
Representative recovered V1 raw SHA256:
`670854af2add30d6e2b848cd2b80d9e3874de63234ebc1c194459e56bfaa1bc3`.
The ambiguous capacity-16 packet is separately hashed in its forensic inventory.
Public retained raw fixtures and damaged-packet regressions are in `tests/fixtures/early_watch`.

## Bounded capacity observations

These are different natural cohorts, not controlled identical-capacity trials. The
8/16 captures are passive and used zero proof RPC. Both precede the V1 repair; their
original reports are preserved separately from repaired offline classifications.

| Capacity | Elapsed seconds | Launches / standard | Ever watched | Serious | Earlier watch recall | Peak active | Capacity rejects |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8 | 90.18 | 56 / 35 | 17 | 3 | 2/3, 66.7% | 8 | 297 attempts |
| 16 | 100.18 | 56 / 42 | 37 | 6 | 5/6, 83.3% | 16 | 0 |
| 32 | 300.61 | 198 / 130 | 114 | 17 | 15/17, 88.2% | 22 | 0 |

Capacity 8 had one serious candidate previously denied admission by capacity. Neither
other capture had a capacity-caused miss. Two serious candidates in the paired run
were already removed by the time they qualified; TTL/removal timing matters separately
from capacity. The active count distribution in the summary is **event weighted**,
sampled at filter/expiry evaluations, not a time-weighted occupancy distribution.
No production capacity is selected. Of the tested capacities, only 32 could accommodate
the paired cohort's observed peak of 22, but a different cohort at 16 had no rejections.

False watches within each short observation horizon were 15 / 31 / 97 markets.
Their attributed transaction bytes were 1,050,672 / 483,783 / 1,079,647. Attributed
market bytes can overlap when one packet references multiple watched markets; stream
totals count each packet once. Unqualified watches are censored at capture end, not
proven permanent false positives. Per-market byte inventories are retained in the summary.
Filter changes numbered 26 / 62 / 215 (0.288 / 0.619 / 0.715 changes/second).

At capacity 32, watch→serious duration was 2.29 / 6.77 / 80.54 seconds
(minimum/median/maximum for previously admitted candidates), with 0 / 8 / 692 packets
and 0 / 50,321 / 2,883,605 bytes in that interval. Zero means the stream packet arrived
after qualification despite earlier watch admission. No TTL increase is justified.

## Overflow and retention

Offline replay of the old 147 retained normalized packets reproduces all **five**
64-event per-market discards in one market: 69 events across 100.97 seconds, average
0.683 events/second, mean normalized payload 7,856 bytes. The five discarded payloads
were 6,173–8,974 bytes. Their event timestamps include three in the serious candidate's
feature window, but replay places their **eviction at 13:08:30–13:08:53 UTC**, after
the earlier proof. Thus “three timestamps intersect the feature window” is not evidence
that those discards caused that proof failure. Unknown rejected packets cannot be replayed.
Limits 128 and 256 avoid all five discards in that old retained sample.

The repaired live capture exposed a larger burst: **106** discards at 256 events.
Every eviction/gap is surfaced. No discarded event was evicted before a relevant
candidate window ended in the offline replay. Nevertheless global buffer gaps keep
the existing proof engine conservative. Replay of all retained usable packets:

| Per-market count | Capacity-32 overflow events | Peak retained bytes |
|---|---:|---:|
| 128 | 367 | 3,895,276 |
| 256 | 106 | 5,002,539 |
| 512 | 0 | 5,790,330 |

The research CLI now allows 128/256/512 with a 512 default, justified by retained
replay. Global count remains bounded at 8,192, TTL 120 seconds and transaction byte
cap 32 MB. The final 512 setting has **offline validation only**, not a new live proof
pilot. Eviction records now include receipt and eviction time. Capture byte/message,
RPC, archive and duration caps remain enforced. No unlimited in-memory history exists.

## Window certification and paired proof

The practical certificate is scoped to the **observed Pump transaction receipt window**:
ack before required start, active continuous watch, no connection/slot gap, no relevant
undecodable packet, no required eviction, coherent per-market slot/index ordering,
all known native signatures retained, and a later slot after the anchor. Each failed
condition yields INCOMPLETE. It does not claim all-program account mutation closure,
provider replay guarantees, or an authenticated end-of-slot delivery barrier. A request
pong is an acknowledgment, not proof that every matching packet was delivered.

Post-capture review found that a short observed span could incorrectly shorten the
required feature window. This is fixed: the required span is at least the configured
metric window (10 seconds in these candidates). Three of five provisional complete
windows had shorter observed spans and are **downgraded**; the archived capture report
is preserved, and the audited summary reports **2/17 complete observed windows**.
The subsequent [rejection forensics](PROOF_REJECTION_FORENSICS.md) corrected the
earlier prose/gate count of three; the audited JSON already listed two.
Native inventory for a broader retrospective window was not archived, so the three
cannot be certified after the fact. Future reports retain that inventory. Event-time
versus receipt-time closure still needs validation before calibration.

The paired run had 17 candidates, exceeding the minimum natural target of ten:

| Evidence/result | Retrospective | Stream-first |
|---|---:|---:|
| Local anchor at that proof boundary | 4/17 before first proof | 9/17 before stream proof |
| RPC reads | 57 (3.35/candidate) | 34 (2.00/candidate) |
| Direct anchor unavailable | 4 | 0 |
| Reconstruction unproven | 3 | 7 |
| Fee/parity failure | 6 | 7 |
| State synchronization failure | 2 | 1 |
| History/signature budget failure | 1 | 2 |
| Config invalidation failure | 1 | 0 |
| PASS | 0 | 0 |

The 4→9 difference is partly packet arrival during retrospective proof. It must not
be presented as evidence available before the first proof attempt. Stream-first reused
nine local transactions, saved 23 reads (**40.35%**), and eliminated direct-anchor
availability failures in this cohort. RPC reductions also reflect earlier exits from
failed proofs; no successful-proof cost is available. Raw proof statuses use
FAIL_CONTINUITY for both availability and reconstruction, so the table separates them
by recorded reason instead of inventing new proof outcomes.

Seven stream proofs still report INSTRUCTION_EVENT_ORDER_OR_MUTATION_UNPROVEN. The
existing reconstruction intentionally rejects unexplained/outer mutable instructions.
Other failures are integer curve input/output mismatch (three), actual sell transfer
or unexplained wallet mutation (four), recent signature budget exhaustion (two) and
history crossing the atomic account snapshot (one). Full packets are now present for
some of these failures; this task does not change those proof semantics. Complete
BUY PASS and repeated SELL PASS were **not** obtained. Four fences remain necessary.

## Discovery and bandwidth

The old 367 MB pilot lacked a per-program discovery breakdown, so it cannot be
decomposed exactly after the fact. The new two-program baseline measured 215.544 MB:
Pump 30.003 MB, global Fee program **185.541 MB (86.08%)**. Log arrays account for
193.998 MB (90.0%); JSON envelopes 21.546 MB (10.0%). There were 16,379 duplicate-signature
messages carrying 29.353 MB. These duplicate bytes overlap program/log totals and
must not be added to them. 36,814 transactions failed and 59,205 messages contained
no supported event. The Fee subscription references activity beyond the narrow
Pump launch universe, explaining much of the unnecessary global traffic.

Minimum early-watch discovery needs Pump creation/trade events, signature, slot,
receipt time and lifecycle events. The Pump program subscription remains. The global
Fee subscription is removed in the 16/32 pilots; watched config account updates and
the existing onchain proof checks preserve fee/config safety. Both-program baseline
counts include 56 Pump CreateEvents and 52 Fee-subscription copies, but per-signature
creation overlap was not retained, so an exact duplicate-launch claim is not made.
Canonical Pump program emission means the Pump subscription is the primary launch
source; 198 launches were detected in the paired run. This does not establish zero
provider-side missed launches against an independent ground truth.

Observed Pump-only discovery was approximately 1,106 MB/hour versus 8,605 MB/hour
for the two-program baseline. These are different live intervals; the within-baseline
86.08% Fee-byte share is the stronger direct reduction estimate. Native
[logsSubscribe](https://solana.com/docs/rpc/websocket/logssubscribe) does not document
server-side event substring or payload projection, and supports one mention address
per filter. Dropping log/JSON fields locally saves parsing/storage, not received bytes.
Do not replace launch logs with minimal parsed summaries without detection parity evidence.

Capacity-32 measured bandwidth, decimal units, normalized to its actual 300.61-second
bounded pilot elapsed time (including setup/teardown). Discovery is UTF-8 decoded JSON;
Geyser is protobuf application size. These are not compressed wire bytes or invoices.

| Stream | Bytes | Messages | MB/hour | Messages/hour | Bytes/launch | Bytes/watch | Bytes/serious |
|---|---:|---:|---:|---:|---:|---:|---:|
| Discovery | 92,346,984 | 50,206 | 1,105.93 | 601,258 | 466,399 | 810,061 | 5,432,176 |
| Early-watch transactions | 19,843,812 | 4,334 | 237.65 | 51,903 | 100,221 | 174,069 | 1,167,283 |
| Accounts | 438,452 | 1,241 | 5.25 | 14,862 | 2,214 | 3,846 | 25,791 |
| Control/slots | 38,774 | 1,360 | 0.46 | 16,287 | 196 | 340 | 2,281 |

Filtered total is **243.36 MB/hour**, considerably larger than the previous late-watch
32.75 MB/hour because watching starts earlier, covers more markets, and includes
non-trade account references. Do not extrapolate profitability or production cost from
either short cohort. Bytes per successful proof are **undefined** (zero successful proofs).
All four bandwidth classes for all three capacities are in the machine-readable summary.

## Final answers and blockers

1. Historical 98: exact causes unprovable without raw packets; reproduced V1 format
   exclusion in new captures, not proven for each historical rejection.
2. Historical fixable fraction unknown; **124/124 (100%)** in the new forensic baseline
   were repairable format exclusions. Zero adapter rejects in the repaired live run.
3. Serious-candidate early-watch recall **15/17 = 88.24%** in the paired cohort.
4. Local anchors **4/17 before first proof**, **9/17 before stream-first proof**.
5. **2/17 audited complete observed windows**; five provisional, three downgraded.
6. **Zero PASSes**.
7. **No complete BUY PASS**.
8. **No repeated SELL PASS**.
9. **57→34 RPC reads, 40.35% reduction**, 3.35→2.00 per candidate; 91 combined.
10. Peak active **22**, accommodated by tested capacity 32; production capacity undecided.
11. Filtered stream **243.36 MB/hour**, separated above; discovery 1,105.93 MB/hour.
12. Broad global Fee logs, verbose log arrays and overlapping subscriptions dominated
    the new forensic discovery baseline; exact historical breakdown unavailable.
13. Yes: retain Pump launch logs and remove global Fee logs. Measured 86.08% removable
    baseline byte share; do not assume field dropping saves incoming bandwidth.
14. **Synchronized calibration is not justified.** Evidence-before-first-proof remains
    weak; full versus observed/event-time window closure needs validation; final 512
    retention needs live validation; native reconstruction, fee parity, snapshot ordering
    and narrow history limits still reject candidates. No complete BUY or repeated SELL
    proof exists. Both calibration and runner stay blocked.

Source fingerprints distinguish capture code from final post-capture fixes. Full raw
archives are retained as `analysis/early_watch_{8,16,32}_packets.jsonl`; summaries, paired
proof details, decoder hashes and retention replay are reproducible with the read-only
analysis scripts. `early_watch_proof_gate.json` records the blocked readiness decision.

Final validation: **380 tests passed**, Ruff passed, strict mypy passed on 131 source
files. The runner validation gate was exercised and rejected activation. No proof
engine or strategy thresholds were modified; no new live proof pilot was run after
the final certificate/retention hardening.
