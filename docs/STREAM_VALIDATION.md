# Stream validation — purpose-specific

Native logs: 23208 messages, two subscription acknowledgments,
251 tracked-market trade observations, no reconnects or
reported connection/subscription errors. No tracked trade had a missing slot or lower slot than
the prior maximum. Duplicate signatures/events are counted and ignored. Most messages concern
unknown markets and trigger no RPC lookup. Event-rate/gap statistics describe tracked trades,
not the provider's entire trade universe. Zero reported reconnects is not an outage recovery test.

PumpPortal: 22 messages, two acknowledgments,
18 creation observations, all source times estimated and
all slots missing. Free discovery worked during this pilot. Trades were deliberately not
subscribed, so momentum/execution suitability remains UNVALIDATED, not proven unsuitable.
Discovery events never substitute for momentum ticks or executable state.

Native decoded event timestamps are chain-origin program fields but were not verified against
blockTime: classification SLOT_ONLY. RPC is SLOT_ONLY. PumpPortal is RECEIPT_ESTIMATE.
No samples claim VERIFIED_CHAIN_TIME. Receipt time is UTC wall clock; monotonic time measures
local durations only. Neither establishes transaction simultaneity. Gaps between market events
are not proof of stream failure or an unchanged price. Last-event silence is reported even if
the stream sends no further events. Track per-mint cadence and provider traffic separately
in a broader follow-up; this pilot cannot infer venue-wide missing trades.

Native tracked-trade receipt gaps (ms): {"N": 250, "median": 2.9502998804673553, "p75": 57.28902498958632, "p90": 310.5388600844889, "p95": 515.4665951267813, "p99": 1371.676822926379, "max": 2791.4030998945236}.
PumpPortal creation gaps (ms): {"N": 17, "median": 610.8947999309748, "p75": 1310.5903998948634, "p90": 3986.7401999421418, "p95": 4918.63204007968, "p99": 7099.755048062652, "max": 7645.035800058395}.
There were 36 locally stale queue observations rejected, demonstrating why unlimited repeated
pairing on a handful of hot tokens is an inefficient collection policy.

PumpPortal explicitly prices token/account trade subscriptions while new-token/migration
subscriptions are free: [official fees](https://pumpportal.fun/fees/). No metered trade subscriptions
or wallet funding were performed. Receiving discovery does not validate paid-trade coverage.
