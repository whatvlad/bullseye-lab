# Native discovery WebSocket repair — 2026-10-03

The prior PAPER log recorded six ConnectionClosedError disconnects over about five minutes, with connections typically lasting 44–49 seconds. It did not retain close codes or reasons. A keepalive timeout is consistent with that timing but cannot be proven retrospectively.

The live diagnostic passes demonstrated local processing overload: the receiver delivered thousands of packets while ordered event processing awaited database projections. The application buffer filled even when bounded to 16 MiB. Merely enlarging the buffer or suppressing Telegram warnings did not fix throughput.

Changes:

- Independent socket receiver and single ordered processor. Original receipt timestamps survive queueing; source timestamps and entry staleness checks are unchanged.
- A constructor-configurable 8192-message buffer with a separate 16 MiB payload ceiling. Overflow cancels the old generation, invalidates continuity and reconnects explicitly; there is no silent market-event coalescing or claim of recovered history.
- Exact transaction-log duplicate removal across overlapping subscriptions, keyed by signature, slot and SHA-256 of logs. Changed/truncated evidence is not deduplicated. The cache is bounded to 4096 keys and cleared on each connection.
- Native Mayhem trade observations retain state updates but bypass expensive durable strategy processing. Discovery records the exclusion.
- PumpSwap trades retain state updates but only enter durable processing when an open position requires exit watching. The watch is restored on startup and updated on position open/close. Standard Pump.fun entries are unaffected.
- Wallet research pulls small batches of unprojected durable trade events from PostgreSQL. Ingestion sets a wake signal carrying no event payloads. There is no RAM event queue to overflow. Transient projection errors retry independently and cannot restart the WebSocket or block exit processing. Terminal wallet flags reconcile from durable token state after restart. Wallet notifications/statistics may lag while old work is replayed.
- Nonterminal curve-progress events no longer recalculate up to 100 wallet metrics because they change no wallet lifecycle fields.
- Invalid Pydantic event data explicitly invalidates native continuity and records only field/type diagnostics. An invalid sample is not treated as valid or as a broken transport.
- Safe close-code/heartbeat classification, receive/processing counts, duplicates, buffer size and lag telemetry; no credentials, URLs or arbitrary remote close reasons are logged.

Validation: 484 tests passed; Ruff passed; mypy passed for 138 source files. The final live bounded observation is in `analysis/websocket_repair_validation.json`, generated from `analysis/paper_websocket_standard.stderr.log`. This is a short operational observation, not a guarantee of permanent provider availability.

PAPER uses the existing portfolio and configuration history. No balance/history reset, strategy threshold change, heartbeat disabling, runner activation or live trading occurred. Final atomic execution refresh and independent HTTP RPC exit monitoring remain mandatory.

Final live check: 01:22:11–01:25:10 UTC (~3 minutes), at least 152,000 processed messages, 9,976 duplicate notifications removed, zero disconnects/overflows, no wallet projection errors. Sampled processing lag peaked at 1,235 ms and ended at 24 ms. Queue peak was 1,483 messages, ending at 35.

Two events failed the positive `quote_amount` constraint. They were explicitly logged and native continuity invalidated; they did not restart the transport. Their original values were not retained by these diagnostics, so this check does not prove whether they represent legitimate zero-output on-chain trades or decoder/schema disagreement. Such samples remain unusable as ordinary executable-price evidence. Provider packet completeness or permanent connectivity is not claimed.


## Correction after the longer run

The first three-minute success window was insufficient. At 01:26:04 UTC the bounded optional wallet queue filled; its QueueFull handler raised RuntimeError into the provider loop. The old log subsequently recorded 212 such failures. This was an introduced coupling defect, not evidence of a new provider outage.

The wallet task had also stopped on PostgreSQL SQLSTATE 22003 (numeric field overflow). A wallet MFE exceeded the ten integer digits available in NUMERIC(18,8). Migration 20261003_0017 widens only wallet outcome percentage fields to NUMERIC(50,8), preserving scale and existing observations. No paper accounting fields or historical prices were rewritten. The previously failing database replay then succeeded. Large stored observations are not thereby validated as trustworthy market returns.

The replacement DurableWalletProjector polls the already persisted unprojected trades, using wallet observation IDs as idempotent acknowledgments. A payload-free wake signal cannot overflow. Terminal flags reconcile from durable token state. Projection exceptions retry without reaching the provider loop. Work is limited to one historical trade and one terminal outcome per batch, with a two-second gap; no new batch begins while the native receive queue is nonempty. Optional wallet history/notifications may lag, while market ingestion and HTTP RPC exits have priority.

Regression coverage includes 10,000 wakeups during a blocked projector, retry after a database failure, restart recovery, idempotent trade/lifecycle replay and migration on SQLite. Full suite: 487 tests; Ruff and mypy (139 source files) passed. The final observation is recorded separately in analysis/wallet_runtime_repair_validation.json.

Final corrected observation: 01:49:47–01:56:01 UTC (6 minutes 15 seconds), at least 305,000 processed stream messages and 19,867 duplicates removed. Zero reconnects, zero wallet projection retries/errors, and one explicitly quarantined invalid price sample. Final sampled queue lag was 12 ms. Wallet observations increased from 344,227 to 344,254 during the check, confirming the projector continues instead of remaining disabled. The observation exceeds the prior 4-minute-53-second time to first queue failure.

Repeated invalidations now avoid cloning states when every updated field already equals its existing value. All invalidation records, reconciliation requests and config generation updates remain unchanged; this is a processing optimization, not proof relaxation. The bounded sample does not establish permanent provider availability. Final PAPER portfolio and strategy settings remain unchanged.
