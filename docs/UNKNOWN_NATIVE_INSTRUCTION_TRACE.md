# Why 93.2% of decisions end with UNKNOWN_NATIVE_INSTRUCTION

Read-only investigation, 2026-10-08. No code, config or runtime state was changed.
Scratch scripts lived outside the repo; they only imported repo code and read
retained logs/packets.

## TL;DR

Every ordinary Pump.fun trade contains a **silent self-CPI** (Anchor `emit_cpi!`
event emission: `Program 6EF8… invoke [n]` → `consumed ~2149` → `success`, with no
`Instruction:` log line). The live feed is `logsSubscribe`, which carries no
instruction data, so `scope_native_mutations` cannot verify that frame and labels it
`UNKNOWN_NATIVE_INSTRUCTION`, bound to **the same market the trade is on**. That
invalidation is applied *before* the trade itself is observed, so every trade after
a market's first one lands as `continuity_status=UNKNOWN`. The price is therefore
always unconfirmed, and the feature engine nulls price change and window coverage.

The only mitigation is verifying the CPI from full Alchemy packets. Those packets
cover at most the first 8 eligible new launches, for ≤120 s each, not the
candidates being evaluated. The live lookup cache recorded **0 hits** in every
retained run.

**Smallest fix proposed:** when no full transaction is available, recognise the
event-CPI frame by a strict log shape (parent is an ordinary Buy/Sell with exactly
one emitted event, silent child of the same program, no data, no children). The
shape was checked against the 6,873 retained full packets: **3,703 of 3,703
matching frames are byte-verified event CPIs**, with zero counter-examples. This
reverses a rule the previous agent wrote down deliberately (see §6), so it needs
your approval.

---

## 1. End-to-end path (files and functions)

| Step | What happens | Where |
|---|---|---|
| 1. Arrival | One WebSocket: `logsSubscribe {"mentions":[6EF8…]}` + `accountSubscribe` on the Pump fee config. Each `logsNotification` = signature, slot, `logs[]` only. | `providers/solana/pump.py` `_process_messages` (L607–627), `_consume` (L436) |
| 1b. Full packets (side path) | Alchemy Yellowstone gRPC, filter `account_include` = accounts of ≤8 watched mints, `account_required=[Pump]`. Packets are converted to RPC shape incl. `innerInstructions` and `loadedAddresses`. | `alchemy_evidence.py` `update_filter` (L203), `rpc_packet` (L88); `operational_evidence.py` `OperationalEvidenceCache` (watch = `EarlyWatch(8)`, L50) |
| 2. Parse | Invocation stack rebuilt from `Program X invoke [d]` / `success` lines. Pump/PumpAMM/Fee frames are kept with their `Instruction:` name and decoded `Program data:` events. | `invalidation.py` `native_frames` (L78); `pump.py` `extract_anchor_events` (L106) |
| 3. Classify | `_apply_notification` looks up a full tx (`transaction_evidence_lookup`, a cache of watched packets only), then calls `scope_native_mutations`. Frames verified as event CPI are skipped. Everything else gets DECODER_FAILURE / KNOWN_NON_RESERVE_MUTATION / MIGRATION / CONFIG_CHANGE / **UNKNOWN_NATIVE_INSTRUCTION** and calls `tracker.invalidate`. | `pump.py` `_handle_notification` (L709), `_apply_notification` (L768, classify at L789); `invalidation.py` `scope_native_mutations` (L164), `verified_event_cpi_frames` (L116) |
| 4. State update | **After** classification, each decoded `TradeEvent` goes to `MarketStateTracker.observe`. If the previous state is not FIRST/EXACT/RPC_VALIDATED, the new state is `UNKNOWN` and inherits the invalidation reason. A trade with a reason attached is published as `TokenTrade.normalized_state`. | `pump.py` `_normalize_and_publish` (L819, observe at L931); `market_state.py` `invalidate` (L294), `observe` (L433, `invalid` at L518) |
| 4b. RPC anchor | Risk-path account refresh can reset a market to `RPC_VALIDATED`. It is accepted only if no invalidation revision happened during the read, which an actively traded market rarely satisfies. | `paper/market_refresh.py` L69, L156–194; `market_state.py` `reconcile` (L650) |
| 5. Features | `ingest_trade` stores `marginal_price = observational_price` (None unless continuity is FIRST/EXACT/RPC_VALIDATED). `_build_snapshot` nulls `latest_price` and every window's `price_change_percent` when the tracker's current state has no observational price. | `intelligence/features/engine.py` `ingest_trade` (L137), `_build_snapshot` (L262, L274) |
| 6. Decision | `missing_price_inputs` → `decision_price`, `rolling_price_change`, `price_provenance`, `price_window_coverage` → `UNKNOWN_REQUIRED_PRICE_CHANGE` → SKIP. | `strategies/price_signal.py` (L8); `strategies/runner.py` `_decide` (L99–117); triggered from `apps/worker.py` `process_event` (L329) |

## 2. Where UNKNOWN_NATIVE_INSTRUCTION is assigned

Two places:

1. **`invalidation.py` L246–256 (the one that matters).** This applies to a native frame that is
   not a verified event CPI, not in `ORDINARY` (Buy, Sell, BuyExactSolIn, BuyExactQuoteIn,
   BuyV2, SellV2, BuyExactQuoteInV2), not a decoder failure, not proven
   write-free by the IDL, not "Migrat*", and not config-ish. A **silent** frame has
   `instruction=None` → `instruction_schema(program, "")` is None → it falls through
   to UNKNOWN. When it is a self-CPI, its market is taken from the parent's event
   (L195–207), so scope is MARKET/POOL with dimensions
   `reserves, identity, config` (L269–274).
2. `market_state.py` L326–327: lower-case reasons containing "unsupported" are
   normalised to it. No live caller found that passes such a reason.

### Real counts from logs (`runtime_metrics.native_instructions`, last line of each run)

Latest retained run, `operational_recovery_processing_20261006.err.log` (10 min):

| Label (reason:program:instruction) | Frames | Share of UNKNOWN |
|---|---:|---:|
| UNKNOWN:**Pump 6EF8…:SILENT** | **33,344** | **93.2%** |
| UNKNOWN:PumpAMM pAMM…:SILENT | 1,278 | 3.6% |
| UNKNOWN:Pump:BuyExactQuoteInV3 | 434 | 1.2% |
| UNKNOWN:Pump:CreateV2 / Create | 364 / 4 | 1.0% |
| UNKNOWN:Pump:SellV3 / BuyV3 | 284 / 1 | 0.8% |
| UNKNOWN:Fee pfee…:SILENT | 57 | 0.2% |
| UNKNOWN:PumpAMM CreatePool / InitBoost; Fee CrankDonationFeePda | 13 / 11 / 1 | <0.1% |
| *(for comparison)* VERIFIED_EVENT_CPI | 1,813 | n/a |

The other three Oct 5–6 runs show the same shape: Pump SILENT is 20,255, 11,462 and
36,242 frames. The Oct 3 run was dominated by PumpAMM SILENT, before PumpSwap was
excluded. The frame-level 93.2% matching the decision-level 93.2% is a coincidence;
the decision figure comes from a different run (below).

The 469 figure comes from `analysis/current_no_trades_audit.json` (Oct 7, 19:02–19:15,
503 active decisions). Over the same window, persisted trades were **18,353 of 19,812
UNKNOWN/UNKNOWN_NATIVE_INSTRUCTION (92.6%)**, 346 FIRST_OBSERVATION and only **49 EXACT**.
**No log of the Oct 7 run is in the folder**, so its per-label counters can't be
read. The Oct 6 counters above are the closest evidence.

### Direct reproduction (repo code, real transaction from `research_sessions/state-trust-20261001`)

```
logs only    trade 1: continuity=FIRST_OBSERVATION invalidation_reason=None price=set
logs only    trade 2: continuity=UNKNOWN           invalidation_reason=UNKNOWN_NATIVE_INSTRUCTION price=None
with full tx trade 1: continuity=FIRST_OBSERVATION invalidation_reason=None price=set
with full tx trade 2: continuity=EXACT             invalidation_reason=None price=set
```
Across all 23 retained transactions: logs-only gives 23 `UNKNOWN:Pump:SILENT`, while
the full transaction gives 22 `VERIFIED_EVENT_CPI` + 1 (under CreateV2).

## 3. Hypotheses

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Inner instructions (CPI) not requested/parsed → router swaps invisible | **Ruled out as stated; the true cause is a close relative.** Router swaps *are* seen: the invoke stack is parsed at any depth. Example: router `MAyhSm…` → Pump `BuyV2` at depth 2 decodes fine. What logsSubscribe lacks is the inner instruction **data** of the event-emission CPI, which is cause #1. | `native_frames` handles depth; sample logs in `research_sessions/state-trust-20261001` |
| v0 transactions: ALTs unresolved → program IDs/accounts misread | **Ruled out.** On the live path, program IDs come from validator log text, and ALTs don't apply there. On the full path, `rpc_packet` carries `loadedAddresses`, and `verified_event_cpi_frames` appends writable+readonly in the correct order (L123–124). Retained version-0 packets verify correctly (3,703/3,703). | `alchemy_evidence.py` L165–168; replay above |
| Unknown programs/discriminators (new AMM versions, routers, ComputeBudget/System noise) | **Partly confirmed, minor.** ComputeBudget/System/Token frames are never classified, since only Pump/PumpAMM/Fee frames are kept (`PROGRAMS`, L18). Confirmed: new Pump instructions **BuyV3, SellV3, BuyExactQuoteInV3** are not in `ORDINARY` and are **absent from the bundled IDL** (`idl/pump.json`, 0 matches), so they become UNKNOWN (≈2% of frames). Also CreateV2, PumpAMM InitBoost/CreatePool, Fee CrankDonationFeePda. | counters above; `grep V3 idl/pump.json` |
| Subscription missing fields (maxSupportedTransactionVersion, encoding, inner instructions) | **Ruled out.** `logsSubscribe` takes no such options and returns logs for every tx version. The Yellowstone filter returns full meta incl. inner instructions. Of 4,109 full packets, 2,237 were dropped by `normalize_transaction`, which requires exactly one standard non-Mayhem SOL trade. That is a scope filter, not missing fields. | `pump.py` L615–618; `evidence_stream.py` L107–142; Oct 6 transport metrics |
| History starts too late → no confirmed baseline | **Ruled out as the cause.** Each market gets a FIRST_OBSERVATION baseline on its first trade (346 in the Oct 7 window). The baseline is then destroyed by the next trade's own silent CPI. The RPC anchor (4b) is also usually rejected, because the market's invalidation revision moves during the read. | `market_state.py` L518; `market_refresh.py` L156 |
| Subscribed accounts/pools ≠ candidates' markets | **Confirmed. It explains why the existing fix doesn't help.** Full packets go only to `EarlyWatch(8)`: the first 8 eligible *launches*, first-come, TTL 120 s, idle 30 s, permanently excluded once removed. Candidates (161 mints on Oct 7) come later, from risk assessment. `cache_hits` never appears in any run's metrics (0), while `cache_misses` reaches 23,850–62,069. In the Oct 6 run only 3,710 trades were on watched markets, and even those were 60% UNKNOWN (1,248 SLOT_REGRESSION from native/full ordering). | `operational_evidence.py` L50, L183; `early_watch.py` L61–88; executed_evidence metrics in the three Oct 5–6 logs |

## 4. Ranking (share of the 93.2%)

1. **Silent Pump event-CPI on ordinary trades, unverifiable on the logs-only path.
   Explains essentially all of it.** The mechanism fires on every trade of every
   market and is reproduced deterministically above. In retained full packets, 96.7%
   of silent Pump frames (3,703/3,830) sit under an ORDINARY parent and all verify.
   `STANDARD_PUMP_FUN_RUNNER.md` already shows the counterfactual: the same trace
   gives 0 EXACT under production trust vs 2,841 EXACT with trade-only arithmetic.
2. **Full-packet coverage aimed at the wrong markets** (8 fresh launches, not
   candidates). This is not an independent cause of the label; it is why cause #1
   was never mitigated for candidates.
3. **Pump V3 instructions** (BuyV3/SellV3/BuyExactQuoteInV3), ≈2% of trade frames.
   These stay UNKNOWN even with a full packet, because the parent is not ORDINARY. Each
   one breaks continuity until an RPC anchor lands. Once #1 is fixed this is the
   biggest residual. Its decision-level share can't be determined from
   current data (see §7).
4. **Silent CPIs under non-trade Pump parents** (CloseUserVolumeAccumulator,
   ExtendAccount, DistributeCreatorFees(V2), InitUserVolumeAccumulator,
   MigrateBondingCurveCreator), 3.3% of silent frames. These are unverified even with full packets.
5. Negligible for candidates: CreateV2/Create (no prior state to break), PumpAMM
   (out of universe), Fee SILENT (GLOBAL, config-only, so it does not touch price
   continuity).

## 5. Smallest fix for cause #1 (proposal, not applied)

In `providers/solana/invalidation.py` only:

- `NativeFrame` gets a `children: int` counter, incremented in `native_frames` when
  a new invoke is pushed under it (2 lines).
- In `scope_native_mutations`, **only when `transaction is None`**, skip a frame
  (count it as `LOG_SHAPE_EVENT_CPI`) if all of these hold:
  `program == PUMP_PROGRAM_ID`, `instruction is None`, no events/raw events, no
  decoder failure, `children == 0`, parent is the same program, parent instruction
  in `ORDINARY`, parent not a decoder failure, parent has exactly one raw event, and
  this is the parent's only silent self-CPI. Truncated logs keep their existing
  invalidation.
- When a full transaction *is* present, behaviour is unchanged: byte verification,
  and the six negative packet tests still hold.

About 15–20 lines. No thresholds, subscriptions, budgets or execution gates change.
Pre-entry execution still requires the atomic RPC refresh and
`execution_*_verified` + HEALTHY (`eligibility.entry_rejection`). A hidden
reserve change inside such a frame would still show up as `CONTINUITY_BREAK` /
DIVERGED on the next trade, because `observe` checks integer reserve continuity.

**V3 (cause #3) is deliberately not included.** Adding them to `ORDINARY` needs
the current Pump IDL with their account lists, plus at least one retained V3 full
packet. Neither is in the repo.

### How to verify

1. **Offline, before any live run:** replay the 6,873 retained full packets
   (`analysis/early_watch_{8,16,32}_packets.jsonl`, `prospective_capture_packets.jsonl`,
   `filtered_stream_packets.jsonl`) logs-only with the fix. Expect: logs-only
   classification equals full-tx classification for every tx, all 3,703 matched
   frames become LOG_SHAPE_EVENT_CPI, and non-ORDINARY-parent frames stay UNKNOWN.
2. **Tests:** `test_real_executed_event_cpi_is_verified_but_not_silent_unknown`
   asserts logs-only is *worse* than full-tx, so its expectation must change. That
   is an intended behaviour change. Add negatives that must stay UNKNOWN: silent child
   with its own invoke, with `Program data:`, under a non-ORDINARY parent, under a
   parent with 2 events, and with truncated logs.
3. **Live PAPER run of the same length, then `analysis/audit_current_no_trades.py`.** These are expectations, not promises:
   - native counter `UNKNOWN_NATIVE_INSTRUCTION:6EF8…:SILENT`: from ~33k / 10 min to roughly 3% of that (~1k); `LOG_SHAPE_EVENT_CPI` takes the rest.
   - `trade_states` UNKNOWN_NATIVE_INSTRUCTION: from 92.6% of trades to under ~15%; EXACT from 49 to the majority (the runner-doc arithmetic replay suggests ~70%+).
   - `price_reasons` UNKNOWN_NATIVE_INSTRUCTION: from 469/503 (93.2%) to well under 30%, with the residual mostly V3. `missing_required_input:price_window_coverage` should drop by a similar amount.
   - **Safety metric:** CONTINUITY_BREAK/DIVERGED trades are ~0.5% today (101/19,812). If they climb above ~2%, the shape rule is hiding real mutations. Revert.

## 6. Earlier write-ups, checked against the code

- *"Ordinary Pump trades include silent self-CPI event emission. Logs alone cannot
  distinguish that emission from an unknown state mutation"* and *"never whitelist
  a silent native frame based only on logs"* (`OPERATIONAL_STREAM_FIXES.md` L177,
  L181; also `STATE_TRUST_MODEL.md`, `INVALIDATION_SCOPING.md`,
  `STANDARD_PUMP_FUN_RUNNER.md`). **Diagnosis correct; the conclusion is a policy choice.**
  Strictly, logs can't show the CPI's bytes. But the event bytes already appear in
  the parent's `Program data:` line. Anchor logs `Instruction: X` for every normal
  handler, so a silent dispatch is the event handler. And 3,703/3,703 shape matches verified. The proposal
  replaces a byte proof with a shape rule plus the downstream continuity check.
  **That trade-off is your call.**
- *"Full-packet availability for at most eight watches does not supply complete
  evidence for every discovery"* (same doc). **Correct**, and it understates the problem:
  the watch never targets candidates, and the live cache hit count is 0.
- *"Earlier fixes reduced processing load"*: **correct**. Queue age dropped to 309 ms
  peak in the Oct 6 processing run, but those fixes don't touch classification.
- `CURRENT_PAPER_ENTRY_BOTTLENECK.md` (Oct 2–3) blames signal expiry and 20 s
  receive delay. That was a different code generation; the Oct 6 run shows ≤309 ms
  queue age. The doc is out of date for this problem.
- `unsupported_native_mutation` in `pump.py` L143 (ORDINARY list without V2/V3)
  is only used by research scripts, not the live path.

Docs coverage: every `.md` was searched for this path (event CPI, silent frames,
UNKNOWN_NATIVE, watch set, V3). The docs above were read in full.
`PROSPECTIVE_HISTORY_BOUNDARIES.md` (1.1 MB) is a data dump and was only searched.
There is no AGENTS.md in the folder.

## 7. What can't be determined from the code and logs here

- **Per-label counters for the Oct 7 run that produced 469.** Its log isn't
  retained. To settle it, keep the next run's stderr: the `runtime_metrics`
  `native_instructions` line.
- **How much V3 contributes at decision level.** This needs the `invalidation_reason`
  *detail per trade* (instruction name), or a run after fix #1. Adding V3 safely
  also needs the current Pump IDL with BuyV3/SellV3/BuyExactQuoteInV3 accounts and
  one retained V3 full packet.
- **Whether any of the 161 candidate mints were ever in the 8-slot watch.** Watch
  admission history isn't logged. Joining `executed_cache.watch.history` to decision
  mints would answer it.
