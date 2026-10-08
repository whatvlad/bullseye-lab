# Operational PAPER stream correction

## October 6 recovery changes (current implementation)

The October 5 incident had two distinct failure paths: overload in the native
receive queue, and keepalive timeouts with an empty queue. `CONNECTED` only
describes transport readiness; it does not certify price history or execution.

- Drop failed transaction notifications at receipt, before the successful-event
  queue. The downstream decoder already discarded them. Subscription responses,
  successful transactions, malformed messages and account updates keep their
  existing paths. A 10,000-message failed-transaction burst is covered by a test.
- Avoid rebuilding exit-only feature windows on every trade for a mint without
  an open position. Scheduled strategy snapshots are unchanged. Position pins
  continue to request per-trade exit features and prioritize queued exit work;
  the execution engine still reads the actual position and fresh atomic state.
  The no-orders diagnostic does not enqueue execution work at all. Remove the
  redundant list-all-open-positions query before each queue pop.
- Limit pending wallet-trade IDs before joining their domain-event JSON payloads.
  On the retained PostgreSQL database, the previous one-row background query took
  1,052 ms and touched about 2.18 million shared buffers; the limited-subquery form
  took 177 ms and about 45,000 buffers in a subsequent read-only EXPLAIN ANALYZE.
  These are separate measured executions, not a controlled cache benchmark.
  Backfill stays ordered, idempotent, and recovers late-arriving older trades.
- Replace the global fee-program log subscription, which also carries PumpSwap
  fee reads, with a subscription to the canonical Pump fee configuration account.
  Changes invalidate config trust. Final atomic execution RPC refresh is still
  mandatory; account streaming does not authorize a fill.
- Retain successfully applied `(signature, slot, log digest)` keys in bounded
  memory. Late native duplicates cannot invalidate a full-packet-verified trade
  after the packet cache expires. Changed/truncated logs still pass the guards.
- For the existing maximum-eight-market watch set, allow a bounded two-second
  native/full-packet arbitration window. The global native publisher does not
  wait. Missing full packets fall back with their original receipt timestamps and
  remain UNKNOWN where proof is missing. Both queues have packet/byte limits.
- Keep healthy stream history at its own sequence when a newer atomic risk RPC
  snapshot arrives. Invalid history still requires reconciliation with the
  existing revision/race checks. Rejected older slots cannot populate features.
- Invalidate historical price samples after a transport gap. A later reconnect
  cannot silently turn a pre-gap price window into continuous history.
- Use the official Alchemy PubSub endpoint, ping timeout 60 seconds and a separate
  20-second data-idle watchdog. The watchdog keeps stalled data actionable even
  with the longer ping tolerance. Queue age, loop lag and observed ping latency
  are logged. These settings are transport controls, not strategy thresholds.
- Record safe field/type and traceback-frame diagnostics for packet errors and
  retain at most five bounded public-packet replay files. An error writing a
  diagnostic file cannot terminate processing. A malformed deferred packet
  invalidates coverage and does not prevent the next pending packet from running.

### Explicitly approved continuous streaming allowance

The local `.env` now selects
`BULLSEYE_SOLANA_EXECUTED_STREAM_HOURLY_BYTES=128000000`, as explicitly approved by
the user. This is a decimal 128 MB rolling-hour payload ceiling, with a further
3,072,000,000-byte rolling-day ceiling. Conservative minute buckets and durable
64 KiB reservations can pause below the nominal ceiling. Budget exhaustion closes
the stream, invalidates coverage and waits until allowance becomes available.
Reconnection does not reset consumption. Healthy sessions reset the consecutive
connection-failure counter; three consecutive unsuccessful sessions still stop.

The ledger is `analysis/runtime/executed_stream_budget.json`. Preserve it across
restarts. Corruption fails closed. The discovery instance lock provides its single
owner. Do not delete it to restart the feed. Example configuration defaults to 0
(the previous session-only mode) to avoid silently authorizing recurring spend on
other installations.

The meter covers received protobuf payloads, including transaction, account and
control packets. Transport framing, provider buffering/billing and other RPC or
WebSocket traffic are separate; this is not a provider-enforced dollar cap.

### Verification status

Ruff and mypy pass; regression tests cover packet deduplication, unknown-data
guards, gap history, atomic-state races, error recovery, failed-packet burst
filtering and persistent hourly/daily budgets. Strategy thresholds, live trading
and the runner block were not changed. Diagnostics disable all PAPER orders and
Telegram. Entry controls are left paused after diagnostics.

An intermediate October 6 run still overflowed at 8,192 queued messages and
10.987 seconds queue age; its log is
`analysis/operational_recovery_final_20261006.err.log` (despite the historical
filename, it is NOT the final corrected validation). That run was stopped to
apply the failed-transaction prefilter. See the filtered run report below for
post-correction measurements.

The first ten-minute filtered run (18:23:33–18:33:41 UTC) had zero disconnects,
overflow or processor errors, but deteriorated to 39.660 seconds queue age and
5,471 queued messages. It is retained as
`analysis/operational_recovery_filtered_20261006.json` and the matching log and
metrics files. It does NOT establish that processing lag was fixed. This exposed
the successful-event processing bottlenecks corrected above.

Read-only replay after that correction used 3,000 retained trades. The old
no-position feature path took 2.559 seconds; the corrected path took 0.391 seconds.
All 551 emitted strategy snapshots matched field-for-field, excluding their
newly generated ingestion timestamps. The comparison retains per-trade exit
features for open positions. See `analysis/feature_work_benchmark_20261006.json`.

Two contemporaneous read-only RPC calls found a confirmed-bank timestamp age of
0.875 seconds. Twenty recent trade receipts were about 0.94–1.23 seconds after
source timestamps. This sample does not support attributing the observed
ten-second queue backlog to chain clock drift. Raw figures are in
`analysis/chain_clock_20261006.json`.

### Completed ten-minute processing validation

The retained run finished on October 6, 18:37:41–18:47:53 UTC. Results were
reviewed on October 7 after the session interruption; no duplicate pilot was
started. PostgreSQL is healthy, no bot process remains, there are no open PAPER
positions, and entries remain paused.

| Measurement | Result |
| --- | ---: |
| Observed launches | 381 |
| Persisted trade events | 13,760 |
| Added PAPER orders | 0 (execution disabled) |
| Native buffer overflows | 0 |
| Maximum sampled native queue age | 309 ms |
| Logged native queue peak | 183 messages |
| Maximum sampled event-loop lag | 38 ms |
| Native connection failures | 1 |
| Transport full packets | 4,119 |
| Packets accepted by the existing normalizer | 1,882 |
| Packets admitted to the active watch processor / processed | 1,880 / 1,880 |
| Full-packet processor failures / overflows | 0 / 0 |
| Full-packet processor queue peak | 16 |

The single native failure was `ConnectionClosedError` with neither a received nor
sent close frame, an empty queue and zero queue age. Its network/provider cause
cannot be established from this evidence. Automatic reconnect recovered it.
There were no keepalive timeout errors in this window. The full gRPC source had
one connection throughout; its reported disconnect was the bounded shutdown.
A ten-minute run cannot establish indefinite transport reliability.

Filtered payload bytes were 21,530,755 transaction, 723,779 account and 70,925
slot/ping/pong bytes: 22,325,459 total. Over the actual 611.53-second observation
this corresponds to approximately 131 MB/hour; it is not a prediction for future
cohorts. At a sustained rate above the approved budget, streaming must pause.
Native discovery and other RPC billing are separate.

### Remaining integrity blockers and October 7 scoped correction

This was a transport/processing diagnostic, not a successful entry proof run.
The watched cohort had 117 EXACT, 73 FIRST, 30 DIVERGED, 2,253 UNKNOWN and 1,248
SLOT_REGRESSION observations. Across the full persisted native population,
8,828 trades still carried `UNKNOWN_NATIVE_INSTRUCTION`. Full-packet availability
for at most eight watches does not supply complete evidence for every discovery.
Unsupported instructions, incomplete packets, ordering and history gaps remain
rejected. The combined normalizer rejection counter alone does not establish the
individual causes of all 2,237 rejected packets.

Of 226 active-strategy decisions, 225 were SKIP and one WATCH. 220 lacked required
price-window coverage. Therefore the runner remains BLOCKED; eliminating queue
overload has not made the entry evidence sufficient. No strategy thresholds or
proof requirements were relaxed.

The run also identified two `quote_amount > 0` validation failures. On October 7,
non-positive Pump trade amounts were changed to explicit, market-scoped rejection
before domain-event construction. Only the affected reserve state and price
history are invalidated; the sample cannot become a valid trade or fill. Tests
cover both zero-token and zero-quote cases and preserve another market's state.
Other unlocalized validation failures still fail closed and now also invalidate
price-window history. This small final correction was regression-tested, not
represented as part of the October 6 live measurement. The older October 5
deferred `ValidationError` had insufficient detail to prove it was the same cause.

Final verification: Ruff and mypy pass; 563 regression tests pass. Evidence:
`analysis/operational_recovery_processing_20261006.json` and
`analysis/operational_recovery_processing_20261006.err.metrics.json`.

## Earlier implementation and evidence

## Scope and diagnosis

The 2026-10-03 operational run observed 887 launches and 33,407 trades, but produced no orders. Of 1,330 active strategy decisions, 1,300 carried `UNKNOWN_NATIVE_INSTRUCTION`; 1,328 lacked required price evidence. Four receive-buffer overflows and twelve WebSocket disconnects were recorded. A connected socket did not imply usable market history.

Ordinary Pump trades include silent self-CPI event emission. Logs alone cannot distinguish that emission from an unknown state mutation. Full executed packets can establish the Anchor emit-CPI discriminator, exact event-authority account, matching event bytes, successful execution and instruction/log alignment. Unsupported instructions still invalidate state.

## Changes

- Verify emit-CPI using retained full transaction evidence; never whitelist a silent native frame based only on logs.
- Reuse a bounded Alchemy stream for at most eight standard, non-Mayhem SOL Pump markets, discovered through the existing cheap native feed. TTL and lifecycle removal remain enabled.
- After explicit user approval, feed complete packets through the existing native decoder and PAPER event bus. The processor queue is bounded to 128 packets and 4 MB. Per-market serialization and deterministic event IDs prevent double projection of native/full copies.
- Project registry and outcome updates in one database transaction rather than two commits per event. Failed projection rolls back both.
- Reuse already-required atomic risk RPC snapshots as current state anchors only if no invalidation occurred during the read. Delayed mutations from older slots cannot invalidate a newer anchor; slotless disconnects still invalidate it. No retrospective RPC budget was increased.
- Surface instruction classifications, full-packet processing, queue overflow and transport diagnostics. An overflow or failed stream invalidates watched state rather than silently claiming complete coverage.

The full stream has a configurable 32 MB default lifetime session budget (`BULLSEYE_SOLANA_EXECUTED_STREAM_SESSION_BYTES`). Exhaustion stops it; there is no automatic budget reset. Native observation continues with strict evidence guards. This budget is not an assurance of indefinite stream availability.

## Verification and limitations

Ruff, mypy and 539 regression tests pass after connecting the approved processor. Tests include seventeen retained real packets, malformed evidence rejection, duplicate native/full projection, independent market locks, projection rollback and atomic-state race/slot protection.

Two preliminary three-minute runs had zero buffer overflows and zero added orders. The first had two keepalive ping timeouts; the second had no disconnects. These short windows do not establish long-run reliability. The cache-only second run still had no EXACT observations and exposed delayed older-slot invalidations; it is not a successful corrected trading run.

Late full packets cannot retroactively repair a previously persisted unknown trade or missing price window. Genuine unknown instructions, non-trade mutations, missing history and configuration uncertainty remain blocked. No claim of COMPLETE_FOR_WINDOW is made. Runner calibration and `runner-edge-prospective-v1` remain blocked; live trading, strategy thresholds and Telegram startup were not changed.

See `analysis/operational_stream_run_audit.json` and the three numbered operational validation log pairs for the measured evidence. The final validation summary is `analysis/operational_stream_validation.json`.

## Approved packet processor: measured window

2026-10-03 23:36:43–23:39:52 UTC: 70 discoveries, 1,036 persisted trade events and zero added orders. The filtered source delivered 204 transaction packets, of which 201 were usable and all 201 were processed. There were no processor failures or receive-buffer overflows. The processor queue peaked at 21 packets. Transaction payloads consumed 1,202,541 bytes; account payloads consumed 78,051 bytes. Transport shutdown contributes one `disconnects` count in the Alchemy adapter and is not a live outage.

Watched markets contributed 400 persisted trades: 44 EXACT, 21 FIRST_OBSERVATION, 234 UNKNOWN, 96 SLOT_REGRESSION and 5 DIVERGED. This is an improvement from the cache-only window's zero EXACT, not a matched-cohort causal comparison. Broad persisted trades still included 630 `UNKNOWN_NATIVE_INSTRUCTION` states; unsupported genuine instructions and markets without full evidence remain blocked.

Sampled native receive lag peaked at 2,431 ms and returned to 24 ms near shutdown; sampled queue peak was 2,292 messages. Two native WebSocket failures were keepalive ping timeouts, with zero queued messages at each disconnect. They were not buffer overflow. A three-minute zero-overflow observation cannot demonstrate indefinite stability or rule out event-loop/network/provider causes of ping loss.

This corrects a verified false-unknown mechanism and reduces duplicate projection work. It does not establish that PAPER entries are now generally executable. Missing history, source ordering, remaining unsupported instructions and intermittent native transport gaps remain integrity blockers. The runner remains blocked. Full non-secret aggregates are retained in `analysis/operational_stream_validation3.summary.json`.
