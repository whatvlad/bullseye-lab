"""Render the retained forensic result, preserving original capture files."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT / 'analysis/proof_rejection_forensics.json').read_text())
rows = d['candidates']
text = '''# Retained stream-first proof rejection forensics

Runner and synchronized calibration remain **BLOCKED**. No orders, discovery runs,
provider requests, new subscriptions, capacity changes or strategy changes were made.
This pass used the exact 17 serious candidates from the retained 32-cap capture.
Proof limits remain 12 requests, four successful state signatures, 12 seconds and
2,000 ms freshness. Four raw history fences and a final atomic execution refresh
remain mandatory. No percentage tolerance or disagreement band was introduced.

## Outcome and evidence scope

| Full candidate outcome | Before | After offline replay |
|---|---:|---:|
| PASS | 0 | 0 |
| Reconstruction | 7 | 4 |
| Fee/parity | 7 | 0 |
| Synchronization | 1 | 1 |
| History/signature budget | 2 | 2 |
| Required next response was never captured | 0 | 10 |

The last row is essential: moving beyond a repaired stage does not imply a full
proof PASS. Seven earlier proofs stopped before any history/bank evidence was
collected; six fee-failing proofs stopped before their second history fence.
Case 1 retained two initial fences but no final pair. The replay consumes each
recorded fence/bank at most once and never substitutes an OLD proof response for
NEW, repeats a fence, reconstructs a historical bank from a later snapshot, or
fetches missing evidence. It uses the historical receipt clock solely for replay;
no current execution receipt is exported. Raw stream packets are reusable only
if received by the original NEW proof start. Later raw packets may explain
historical ordering but cannot retroactively become local evidence at that time.

Evidence and all 17 timelines: [machine-readable report](../analysis/proof_rejection_forensics.json).
Replay: `.venv/Scripts/python.exe analysis/replay_proof_rejections.py`.
Inputs: `early_watch_32.json`, its raw protobuf archive and `early_watch_summary.json`.
Their SHA-256 hashes are recorded in the JSON. Original captures are preserved.

### Correction to the previous window count

The user briefing and previous prose/gate said three audited windows. The archived
capture actually has five provisional certificates: cases 7, 8, 9, 10 and 11.
Cases 8, 9 and 11 span respectively 3, 4 and 4 seconds against a required
10 seconds. The existing audited JSON lists **two** valid windows: cases 7 and 10.
The prior wording “two downgraded; three audited” was a reporting error. All five
are examined here, with the two valid certificates prioritized in replay.

Case 7 now has deterministic CPI/event alignment, exact physical accounting and
verified single-transaction reserve reconstruction, but no retained first history
fence or atomic bank. Case 10 has an unexplained direct router-owned lamport
redistribution. Neither valid observed window yields a full candidate PASS.
Case 9 also repairs transaction reconstruction but its four-second certificate
does not certify the configured feature window. An observed transaction window
does not certify all-program account mutations, atomic bank synchronization or
final execution freshness.

## Transaction truth classification

| Original rejection classification | Count |
|---|---:|
| PROOF_ENGINE_FALSE_NEGATIVE | 10 |
| MISSING_EVIDENCE | 3 |
| TRUE_SAFETY_REJECTION | 1 |
| UNKNOWN | 3 |

These classify the demonstrated original blocker, not a whole candidate's
eligibility or trade quality. Ten original stage rejections are repaired: three
reconstruction cases and seven fee/parity cases. They still lack full proof
evidence. The synchronization case has a genuine terminal-state mismatch even
though its original immediate error was misleading. Three unexplained router
redistributions are UNKNOWN, rather than assertions of unsafe markets. One
wrapped-SOL case and the two truncated history cases are missing evidence.

## Generic instruction/event alignment and safe ancillary effects

`trade_alignment.py` finds supported Pump trade instructions at top level or
inside CPI, resolves static and loaded accounts, binds the IDL account positions,
and follows the invocation's recorded stack-height subtree to exactly one
matching emit-CPI TradeEvent. It checks that the typed log event agrees with that
event. Missing nested stack heights, duplicate native calls/events and incorrect
mapping fail closed. No signature or router-address exceptions exist.

`execution_accounting.py` then accounts for every transaction account's lamport
delta, including the actual network fee, and every available token-balance delta.
Known System transfers/creation/seeded creation, exact token transfers, user ATA
initialization, rent deposits and zero-balance token-account closes have explicit
effects. Close refunds use the actual balance at close, verified authority,
program and final zero balance; no fixed rent constant is assumed. SyncNative
requires a known intermediate rent/token boundary. An additional Pump mutation
is explicitly unsupported. Unknown protected CPI mutations and ancillary
transfers touching protected accounts fail closed, even if balances add up.

Nonce advancement, memo, compute budget, user ATA creation and unrelated explicit
tips do not themselves justify rejection. They are accepted only under their
known program semantics and protected-account restrictions, with all CPIs and
balance effects checked. Canonical bank ownership/config/lifecycle verification
remains mandatory. A wrapper is not globally allowlisted: Solana foreign-owner
write restrictions and the inspected CPI subtree provide the conditional boundary.
Packet-local accounting alone cannot approve execution. Canonical mint/vault,
config, fee destinations, creator PDA, supported token extensions, exact reserve
transition and fee arithmetic checks remain in the candidate engine.

Sources: pinned official [Pump IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json)
and [SPL Token processor](https://github.com/solana-program/token/blob/main/program/src/processor.rs).
The local IDL is fingerprinted by the validation gate; live upstream drift does
not silently change these proofs.

## Seven reconstruction cases

All seven exposed the old top-level-only alignment limitation. Only three have
enough additional physical evidence to repair their transaction reconstruction.
Four remain unproven in the supported model; that does not prove their real
market state was invalid or impossible to establish with different evidence.

| Case | Mint prefix | Narrow classification | Result |
|---:|---|---|---|
| 3 | DGrYBd | PHYSICAL_BALANCE_MISMATCH | Router redistribution remains UNKNOWN |
| 5 | B4CXNX | MISSING_PACKET; UNSUPPORTED_INSTRUCTION_VARIANT | Intermediate WSOL state missing; extra Pump close unsupported |
| 7 | CYER54 | PROOF_ENGINE_LIMITATION / EVENT_INSTRUCTION_ALIGNMENT | Exact reconstruction repaired |
| 9 | HbAYxS | PROOF_ENGINE_LIMITATION / EVENT_INSTRUCTION_ALIGNMENT | Exact reconstruction repaired |
| 10 | Hh8joW | PHYSICAL_BALANCE_MISMATCH | Router redistribution remains UNKNOWN |
| 12 | DUtpNP | PHYSICAL_BALANCE_MISMATCH | Router redistribution remains UNKNOWN |
| 13 | 4BEqUn | PROOF_ENGINE_LIMITATION / EVENT_INSTRUCTION_ALIGNMENT | Exact reconstruction repaired |

Cases 3, 10 and 12 have correctly identifiable Pump CPI/event/reserve mutations,
but all-transaction accounting leaves nonzero SOL residuals. Known System/token
transfers and network fees have already been applied. The following are **unexplained
residuals**, not inferred legitimate transfers (prefixes only; full keys in JSON):

* Case 3: 2ApLdw −5,050,505; 4kuG6 +1,767,677; 8ccCL +101,010;
  EKeTv +151,515; ERCFj +3,030,303 lamports.
* Case 10: 2ApLdw −8,918,575; 8ccCL +178,371; 8m5Gk +3,121,502;
  EKeTv +267,557; ERCFj +5,351,145 lamports.
* Case 12: 5vPNE −5,997,653; 8m5Gk +5,997,653 lamports.

Each residual set sums to zero, consistent with a router-owned direct
redistribution, but no explicit CPI transfer or retained router-account ownership/
program semantics proves those movements. Zero-sum is insufficient. The bot
does not ignore them. Token residuals are zero in these three cases.

Case 5 creates, initializes, synchronizes and closes an ephemeral wrapped-SOL
account within the transaction. Its pre/post token metadata does not expose the
intermediate rent/token boundary. A subsequent `close_user_volume_accumulator`
Pump mutation is also outside the supported simple route. The packet does not
justify treating those lamports as an assumed refund; rejection remains narrow.
No general router or Mayhem support was added to repair it.

For all seven, JSON retains every pre/post SOL balance, network fee, pre/post
token row, exact event reserves, CPI coordinates, original/full packet and the
corrected reconstruction result. Successful ledgers contain every movement and
empty residual maps. Rejected ledgers explicitly identify what cannot be
explained; “full packet present” is never substituted for missing state semantics.

## Three integer BUY mismatches

All three used native **exact-input** instructions, while the proof inverted an
exact-token buy. Native exact-input deposits one more lamport than that inverse
in each case. This is instruction/rounding semantics, not a tolerance, incorrect
state boundary, fee tier, creator override or reserve cap.

Pinned `buy_exact_sol_in` IDL documentation specifies:

```text
net = floor(gross * 10000 / (10000 + protocol_bps + creator_bps))
charges = ceil(net * protocol_bps / 10000) + ceil(net * creator_bps / 10000)
net -= max(0, net + charges - gross)
tokens = floor((net - 1) * virtual_tokens / (virtual_quote + net - 1))
```

Protocol/creator fees are then computed with integer ceilings at adjusted net.
`buy_exact_input` implements this branch; SDK construction quotes and inverse
exact-token math remain separate. The captured V2 exact-quote instruction matches
the formula exactly; unsupported completion/cap branches remain explicit rejections.
All three have 95 protocol bps, 30 creator bps and fee tier threshold zero.

| Case | Variant | Gross lamports | Native net | Protocol fee | Creator fee | Native tokens | Old inverse net minus native |
|---:|---|---:|---:|---:|---:|---:|---:|
| 4 | buy_exact_quote_in_v2 | 200,000,000 | 197,530,863 | 1,876,544 | 592,593 | 5,808,275,502,868 | −1 |
| 14 | buy_exact_sol_in | 761,782,899 | 752,378,171 | 7,147,593 | 2,257,135 | 9,883,194,423,530 | −1 |
| 15 | buy_exact_sol_in | 30,000,000 | 29,629,629 | 281,482 | 88,889 | 649,050,083,068 | −1 |

All token quantities are raw base units. Case 4's SDK construction quote outputs
29,230 more raw token units than native exact-input; cases 14/15 output the same
tokens but quote one fewer net/gross lamport. All pre-state values, selected fee
inputs, old inverse, SDK quote and exact native result are in `integer_parity_case`.
The new checks require equality of native event amount, tokens, limit, fees,
destinations and full packet accounting. Retained-packet regressions cover all three.

## Four SELL wallet cases

Actual user delta = net trade proceeds − paid network fee + close refund − explicit tip.
Protocol, buyback and creator fees are already subtracted from net proceeds and
are independently verified against their authorized recipients and native fields.
Every token transfer is separately checked against the canonical vault/event.

| Case / transaction | Net trade proceeds | Paid network fee | Actual close refund | Explicit outgoing tip | User lamport delta |
|---|---:|---:|---:|---:|---:|
| 1 anchor | 82,082,776 | 19,550 | 2,039,280 | 0 | 84,102,506 |
| 1 successor | 7,915,645 | 25,000 | 1,513,840 | 25,000 | 9,379,485 |
| 8 | 259,204,676 | 5,000 | 0 | 1,000,000 | 258,199,676 |
| 11 | 202,555,717 | 18,000 | 2,039,280 | 250,000 | 204,326,997 |
| 16 | 471,896,753 | 505,000 | 2,039,280 | 200,000 | 473,231,033 |

Case 1's original anchor already passed parity. Its **successor** failed: the
actual Token-2022 close refund is 1,513,840, not the old assumed 2,039,280, and it
has a separate 25,000 tip. This is now exact. Case 8 is an explicit unrelated
System tip; cases 11/16 combine close refunds and explicit tips. None requires a
band or unexplained-wallet exception. Each anchor/successor exact ledger records
source, destination, amount, asset, role and instruction coordinate. Unknown
movements and protected account mutation still reject.

## History budget and synchronization

Case 0: each five-row page contains three failed and two successful transactions;
the vault page is entirely in slot 452628555, above anchor slot 452628554. Its
oldest row does not reach the anchor boundary. Failed signatures polluted the
original count, but successful entries still do not prove a bounded closed window.
The corrected engine stops with `successor boundary not reached` within existing caps.

Case 6: both five-row pages contain only failed transactions in anchor slot
452629051, with no anchor visible. Those failures do not mutate market state,
but a full same-slot page without the anchor/older boundary can hide successful
signatures beyond the page. It also remains `successor boundary not reached`.
Neither trace proves that more than four successful state transactions were
required. Neither permits equivalent proof by simply discarding failed rows.

Failed rows are now excluded from reconstruction/signature cost, while all four
raw history fences retain them. A full page must reach the anchor signature or
an older slot before that filtering can help. Tests verify both above-anchor and
same-slot failed-only pages remain blocked, and anchor-bounded failed rows cost
no successful-state signature budget. No extra history request is introduced.

Case 2 ordering (UTC):

* OLD proof 13:50:34.397350–34.755392: terminal state differs from atomic bank.
* NEW anchor is successful SELL, slot 452628678/index 362 (index learned later
  from raw archive, not local evidence at the original proof boundary).
* NEW curve fence receipt 13:50:34.884544: lagging address index, newest slot 452628677.
* NEW atomic bank receipt 13:50:34.956003: bank slot 452628680.
* NEW vault fence receipt 13:50:35.054165: same-slot successful anchor index 362,
  successor index 511, failed transaction index 364, and older rows.
* Raw anchor/successor full stream receipts are 13:50:47.808278/47.809546,
  well after proof. Their indices cannot retroactively solve in-proof ordering.

The original NEW error `history crosses account snapshot` actually fired on the
failed row, not a successful transaction newer than the bank. Filtering repairs
that misleading trigger. The replay then correctly stops at unproven same-slot
order. Even using the later raw indices for **post-hoc diagnosis**, the two
successful events end at virtual tokens 735,003,551,695,664 and quote
43,795,706,775, while the atomic bank has 737,289,921,785,186 and 43,659,894,268.
The missing transition is +2,286,370,089,522 tokens / −135,812,507 quote lamports.
Thus concurrent/unindexed market mutation or missing successful history remains
real; exact causal transaction is not established by this trace. Both OLD/NEW
reject and sequential A/B timing can change which stage is reached. No exact
ordering or bank agreement is fabricated from the later archive.

## Candidate-by-candidate original timeline and replay

All times below are UTC; full identity, raw bank response, history rows and packet
hashes are in the JSON. A null bank or missing fence is explicit unavailable
evidence. Packet indices from late stream delivery are diagnostic only.
'''

for r in rows:
    a = r['alignment']
    bank = r['account_bank']
    bank_desc = (f"slot {bank['response']['context']['slot']} received {bank['received_at']}"
                 if bank else 'NOT CAPTURED')
    fences = '; '.join(f"{h['address']} @ {h['received_at']} ({len(h['rows'])} rows)"
                       for h in r['history_fences']) or 'NOT CAPTURED'
    local = ', '.join(r['local_available_at_start']) or 'none in retained stream archive at proof start'
    text += f'''\n### Case {r['case']}: {r['side']} `{r['mint']}`

Curve `{r['curve']}`. Anchor `{r['signature']}`.
Slot {r['slot']}; archived transaction index {r['transaction_index']}; event ordinal {r['event_index']}.
Instruction `{a['name']}`: top {a['top_index']} → inner {a['inner_index']} (stack {a['stack_height']})
→ event-CPI inner {a['event_inner_index']}. Original proof {r['proof_started_at']}–{r['proof_completed_at']}.

Retained full proof-response packets: {len(r['full_packets_retained'])}. Local at start: {local}.
Recorded original stream reuse: {len(r['original_local_packets_used'])} packet(s).
Bank: {bank_desc}. Fee route: {r['fee_route']}.
History fences: {fences}.

Reconstruction after: `{r['reconstruction_after'][0]['status']}`.
Parity after: {', '.join(p['status'] for p in r['parity_after'])}.
Original: `{r['before']['status']}` — {r['before']['reason']}.
Replay: `{r['after']['status']}` — {r['after']['reason']}.
Classification: **{r['classification']}**. {r['cause']}.
'''

# Exact case-1 successor network fee/delta, without conflating it with its anchor.
case = rows[1]
successor = next(p for p in case['parity_after'] if p.get('result', {}).get('quote', {}).get('net_output') == 7915645)
tx = next(t for t in case['after']['evidence'].get('native_transactions', [])
          if t['transaction']['signatures'][0] == successor['signature'])
from memebot.providers.solana.trade_alignment import account_keys
user = successor['result']['native_fee_fields']['user']
index = account_keys(tx).index(user)
text += f"\nCase 1 successor exact network fee: {tx['meta']['fee']:,}; user delta: " \
        f"{tx['meta']['postBalances'][index] - tx['meta']['preBalances'][index]:,} lamports.\n"

text += '''
## Readiness answers

1. All seven had an alignment limitation; **three of seven** have sufficient
   physical evidence for a justified reconstruction repair.
2. **Four remain unproven**: three UNKNOWN router redistributions and one missing
   intermediate WSOL/unsupported extra-mutation case. No claim of fundamentally
   impossible state or fraudulent markets is supported.
3. All three integer mismatches were native exact-input versus inverse
   exact-token semantics, with **one lamport** difference per case.
4. The four sell failures were exact user-accounting errors: a nonconstant close
   refund plus tip in case 1's successor, a tip in case 8, refunds plus tips in
   cases 11 and 16.
5. Yes: supported unrelated tips, account closes, user ATA creation and other
   ordinary ancillary activity had been rejected unnecessarily.
6. **Zero full retained candidate PASSes** after justified fixes.
7. **Zero valid complete-observed-window PASSes**; audited count corrected to two.
8. No complete BUY PASS; no prospective capture was authorized by replay success.
9. Exact individual SELL parity is repeatable in retained packets; **repeated
   full SELL candidate PASSes were not obtained**.
10. Dominant replay blocker: **10 missing next-step responses**, followed by
    four still-unproven transaction reconstructions, two truncated history
    boundaries and one unsynchronized case. Offline replay cannot retrieve
    a fresh historical bank/fence that was never recorded.
11. No provider, discovery, capacity or RPC-budget redesign is justified by
    these findings. A later explicitly authorized bounded passive run should
    capture the newly reachable proof stages. Unsupported routers can stay
    rejected. Same-slot ordering and missing terminal transitions remain
    evidence problems, not reasons to relax proof.
12. **Synchronized calibration is not justified.** Keep calibration and runner
    blocked until full natural BUY and repeated SELL proofs include canonical
    state, supported fee route, exact accounting, bounded continuity, four
    history fences and mandatory final atomic execution refresh.

Validation: retained-packet and adversarial regressions, whole repository tests,
Ruff and strict mypy results are recorded in `analysis/proof_rejection_gate.json`.
The gate fingerprints the alignment/accounting modules as well as existing
proof/math/identity/stream code. Prior validation receipts cannot authorize this
changed proof code. No live execution or strategy result was measured.
'''
(ROOT / 'docs/PROOF_REJECTION_FORENSICS.md').write_text(text, encoding='utf-8')
print('Wrote docs/PROOF_REJECTION_FORENSICS.md')
