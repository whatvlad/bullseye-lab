# Working filtered executed stream — 2 October 2026

**Alchemy access is working. The proof pilot is only partially successful.
Calibration and `runner-edge-prospective-v1` remain BLOCKED.** No orders or live
trading were enabled; strategy qualification, proof checks, four history fences,
per-proof RPC limits and final atomic execution refresh were retained.

## Provider and access

The signed-in dashboard initially confirmed **Free**. The user upgraded the team,
and the dashboard then confirmed **Active Plan: Pay As You Go**. Using the existing
app key via X-Token at `solana-mainnet.streaming.alchemy.com:443`, Ping succeeded.
The corrected Subscribe applied narrow filters and delivered real executed packets.
This resolved the prior Free-account UNIMPLEMENTED responses.

The reviewed upgrade page stated no monthly fee, $0.525/million base RPC CUs, payment
setup and a temporary $5 card hold. Alchemy publishes streaming at
[$75/TB](https://www.alchemy.com/solana-grpc); billed wire bytes and the actual invoice
are not known. No $499+ tier was purchased. Existing Helius full-transaction access
returned `transactionSubscribe is not available on the free plan`; no Helius
upgrade was needed once Alchemy worked. [Official Alchemy access/auth guide](https://www.alchemy.com/docs/reference/yellowstone-grpc-quickstart).

The initial transport trial combined ping and filter updates and captured no
transactions. Separating them fixed delivery. Its eight candidates and 30 RPC
reads are retained separately as `filter_setup_trial_*` artifacts and are not
included in the working-stream results below. A pong alone did not establish
applied filters or full-packet delivery.

## Dynamic cohort and capture

Cheap existing native logs discover launches and apply unchanged qualification.
Only observed standard Pump.fun SOL launches with EXACT arithmetic continuity and
simple native fee events enter the observational watch set. Known cashback/shared/
holder routes, Mayhem, unsupported quotes, multi-event ambiguity, migration and
completion are excluded cheaply. At most eight markets are watched concurrently;
the filter OR-includes locally derived mint/curve/vault addresses and requires the
Pump program. Per-market TTL/inactivity removes filters. Config account updates are
requested only alongside watched markets. No global full-transaction/account
subscription is used. Derivation does not replace canonical on-chain identity proof.

The 168.98-second working capture observed 99 launches, 71 standard launches
(71.72%), watched 22 distinct markets over time and compared seven natural serious
candidates. It stopped at the **existing 150,000-message discovery cap**, below
the 10–20 serious-candidate target. The aggregate task used **78 of 96 RPC reads**:
30 setup + 48 working paired proof reads. The corrected capture had a remaining
66-read cap; no retrospective budgets were increased.

| Evidence | Measured result |
| --- | ---: |
| Full executed provider packets received | 245 |
| Converted/usable standard packets | 147 |
| Decoder-rejected packets | 98 |
| Normalized packets archived | 147 |
| Serious candidates with local anchor before proof | 3 / 7 |
| Complete certified local history windows | 0 |
| PASSes, in either proof arm | 0 |
| Complete live BUY PASS / repeatable SELL PASS | Neither |

The retained normalized packets include signature, slot, transaction index, message
accounts/instructions, inner instructions, logs, pre/post SOL and token balances,
error status and receipt time. Three candidates could reuse their captured anchors.
One comparison also reused another captured transaction: four `getTransaction`
calls were avoided. RPC was still used for uncaptured transactions and existing
proof duties. No complete local window was claimed to justify skipping fences.

During this pilot the 98 conversion failures did not retain raw packets or specific
decoder reasons. Their cause cannot be proven from the stored evidence. A subsequent
ten-second narrow diagnosis received no packets and cannot resolve that question.
The final adapter now archives raw protobuf **before** conversion and labels
decoder rejections; this repair passed regression tests but was not live re-piloted.
The final pilot also releases failed-candidate watches and prevents re-admission
within that run; this cleanup was added after the measured capture.
Unsupported V1 messages fail closed. Do not assert that V1 caused the earlier 98
rejections. The final-code fingerprints describe the post-capture implementation,
and the summary explicitly records that difference.

## Paired proof results

| Failure class | RETROSPECTIVE | STREAM-FIRST |
| --- | ---: | ---: |
| Transaction availability | 2 | 2 |
| History window / successor boundary | 1 | 1 |
| Native/physical reconstruction | 1 | 1 |
| Same-slot synchronization | 2 | 2 |
| Integer curve/fee parity | 1 | 1 |
| PASS | 0 | 0 |

RETROSPECTIVE used 26 RPC reads (3.71/candidate); STREAM-FIRST used 22
(3.14/candidate), a **15.38% reduction** with the same proof checks. These are
sequential comparisons with independent bank reads, not an atomic A/B experiment.
There is no successful-proof RPC cost to measure.

Transaction availability **did not materially improve across the whole cohort**.
Three of the four candidates without local anchors were outside the active watch
filter at detection; watch admission/capacity/removal therefore remains an evidence
coverage bottleneck. The other missing anchor belonged to a watched market, but
unarchived decoder rejections prevent proving whether it arrived and was rejected.
The stored data cannot distinguish all subscription, delivery and decoder causes.

Fee parity failed on integer curve input/output; reconstruction remained unproven;
same-slot ordering and a successor boundary remained unresolved. These are explicit
rejections, not silently accepted execution assumptions. Proof logic was not redesigned.

## Coverage and bandwidth

One connection, one successful Ping, 51 request-stream pongs, revisions through
43, and 627 confirmed slot updates were observed. First slot: 452618729; last:
452619355. There were no live reconnects or replay/backfill attempts. The final
disconnect was capture teardown. The buffer surfaced one out-of-order transaction,
five per-market overflows, TTL expiration and capture termination. No duplicate
packet event was recorded. Connectivity/pongs/slots do not certify a closed window;
**COMPLETE_FOR_WINDOW remains false**. Account streaming does not replace the bank.

| Stream | Application bytes | Actual pilot rate, decimal MB/hour |
| --- | ---: | ---: |
| Global native-log discovery | 367,078,742 | 8,330.38 |
| Filtered full transactions | 1,402,586 | 29.88 |
| Filtered accounts | 114,219 | 2.43 |
| Slots/control | 20,348 | 0.43 |
| Total filtered Geyser stream | 1,537,153 | 32.75 |

The discovery rate uses its 158.63-second capture interval; Geyser rates use
168.98 seconds including proof drain. JSON discovery and protobuf streaming are
different application byte models. Compression, transport overhead and billed
bytes are unknown. These rates are computed from this filtered pilot, not from
the prior global log capture, and are not projected monthly traffic or bills.

Full-transaction allocation was 63,753.91 bytes per watched market and 200,369.43
bytes per serious candidate. Bytes per successful proof are undefined because
there were no PASSes. The full transaction stream is small in this sample;
global discovery dominates data volume and remains a cost/efficiency limitation.

## Final answers and gate

1. Working configuration: Alchemy mainnet Yellowstone, user-enabled PAYG, X-Token.
2. Required change: Free → PAYG/payment setup; reviewed/published costs above;
   actual billed amount unknown. No $499+ purchase.
3. Packets: 245 received, 147 usable/archived, 98 rejected without raw retention
   in this capture.
4. Local evidence: three of seven anchors; zero certified complete history windows.
5. Candidate PASSes: zero in both arms.
6. Complete live BUY PASS: no.
7. Repeatable SELL PASSes: no.
8. Availability failures: two in each arm; not eliminated or materially reduced.
9. RPC/candidate: 3.71 old, 3.14 new; 48 paired reads, 78 task reads within 96.
10. Filtered bandwidth: 29.88 MB/hour transactions, 2.43 accounts, 32.75 total
    including control; separately 367.08 MB discovery during this capture.
11. Four history fences: still necessary. Delivery/order/overflow gaps prevent
    evidence equivalence; final atomic execution refresh remains mandatory.
12. Synchronized calibration: not justified. It and the runner remain BLOCKED.

Validation: **358 tests passed**, Ruff passed, mypy passed on 128 source files.
The actual runner validation function still rejects activation. Raw evidence,
per-candidate diagnostics, measured costs, limitations and final fingerprints are
in `analysis/filtered_stream_summary.json`; the explicit gate is
`analysis/filtered_stream_proof_gate.json`.
