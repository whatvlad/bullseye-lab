# PAPER exit priority and latency

Previous exits could wait on a shared sequential monitor and its five-second cycle. The native
adapter now recognizes a successful log event for an already watched position on receipt and
schedules an atomic exit evaluation before downstream ingestion/candidate analysis. The ordered
decoder remains responsible for market events. Receipt-only wakes cannot manufacture price or
continuity. A 5s per-market watchdog remains fallback, with 30s bounded recovery attempts.

| Field | Meaning |
| --- | --- |
| event_received_at | Local provider receipt; null for timer-only evaluations |
| event_ingested_at | Original event ingestion timestamp; null on receipt-only wake |
| event_ingested_status | ingested / receipt_only_wake / watchdog |
| exit_evaluation_started_at | Evaluation begins after acquiring the market lock |
| RPC_refresh_started_at | First atomic refresh starts |
| RPC_refresh_completed_at | Last atomic refresh completes; each read also has its own trace |
| exit_triggered_at | A validated executable mark triggers the primary exit policy |
| paper_fill_at | Pessimistic simulated fill on the final fresh bank |
| queue_wait_ms | Receipt wake scheduling wait, or receipt-to-processing wait for ingested events |
| lock_wait_ms | Waiting for that mint's lock; no global monitor lock |
| RPC_ms | Sum of refresh elapsed times, including existing fallback work |
| simulated_execution_delay_ms | Actual compute/submission wait; configured delay also recorded |
| trigger_to_fill_ms | Trigger to simulated fill, including delay and second bank refresh |
| price_change_trigger_to_fill_percent | Final gross executable price versus detection-bank price |

Same-position calls serialize and re-read the current position before action. Different markets
progress independently. The watchdog does not await a slow market before dispatching other
markets on its next cycle. Position close unpins the receipt watch. Fresh banks use a minimum
slot from the received event and last execution mark. Quotes after the delay are refreshed and
soft exits re-evaluated; stale/unavailable state produces recovery attempts, not forced fills.
Final exit risk is net executable liquidation / remaining entry cost basis. A partial-profit fill
diagnostic uses the **full remaining liquidation** for stop risk, not half proceeds / full basis.

An event-to-trigger measurement is latency from an observed local receipt, not proof of when
the market first crossed the stop on-chain. No historical trace establishes comparable old
stop-detection latency. Existing entry-to-fill latency must not be substituted for it.
Network submission/inclusion is not performed in PAPER, so paper_fill_at is not a live confirmation.

Actual distributions and retained per-order traces: `analysis/paper_exit_latency.json`.
Without prospective exits, overshoot and latency improvement remain unmeasured.
