# Production state continuity validation

Runner remains BLOCKED. No orders, positions, live trading, experiment activation,
strategy changes or source-disagreement threshold were authorized or performed.

## Captured historical cases

The production path replayed all 21 selected anomaly/control observations,
including same-slot cases: 18 native Pump.fun POST, two multi-event UNKNOWN, one
PumpSwap reconstructed POST. The two multi-event cases share one three-buy native
transaction; event transitions are internally consistent but log-only production
handling remains UNKNOWN. Original paired RPC samples are still SLOT_ONLY.

All three prior PumpSwap integer breaks now have intervening native trades absent
from retained capture. The previously unresolved pool
`97WA9HpK3j4N4y1qz37trWcdLYjH9x2KcSLRKobwkrT4` spans slots 452381928→452381934.
Five newly read middle blocks reveal a buy at slot 452381929, transaction 825,
signature `2VCHYqq1YTdU25nxuPUve1ccGTSqP8PgUC5PAavPNa91wBq6DJQLHcqmWavntVtqLdsFYqWVBbocxgVtmXDe53u`.
It adds 99,265,784 quote units and removes 452,790,536,007 token units, exactly the
previous residual. All adjacent integer residuals are zero after including it.
This establishes missing retained trade transitions, not the provider/decoder/
buffer/cutoff loss layer. See `analysis/remaining_state_break.json` and the two
other preserved `analysis/live_transition_forensics.json` timelines.

## New bounded passive validation

UTC 2026-10-01 20:16:59.319970→20:17:19.987516, 20.668 seconds. The configured cap
was 60 seconds/30 RPC reads; the inherited 25,000 native-message cap stopped the
capture earlier. It tracked 429 market keys and 3,962 decoded trades. PumpPortal
was free discovery/migration only; no metered trade subscription.

| Continuity classification | Pump.fun | PumpSwap | Total |
|---|---:|---:|---:|
| FIRST_OBSERVATION | 126 | 302 | 428 |
| EXACT | 39 | 55 | 94 |
| DIVERGED: exact nonzero integer delta | 117 | 0 | 117 |
| UNKNOWN: invalidated/unproven history | 884 | 2,439 | 3,323 |

117/3,962 observations (2.95%) reported integer mismatches, all Pump.fun. This
short capture does not establish their causes or a long-run loss rate. 3,323
UNKNOWN observations (83.87%) include sticky invalidation, rather than independent
missing trades. There were 444 unsupported-native-instruction transactions and
23 truncated-log transactions. Conservative global invalidation explains much
of the low usable continuity count; it must not be presented as a measured stream
delivery failure rate. Unknown observations do not manufacture flat prices.

Observed mutations: 1,858 buys, 2,104 sells and 15 native creates, plus the above
unsupported/truncated classifications. Evidence is in
`analysis/production_state_passive.json`; all normalized observations and RPC
duty records are retained. No representative percentage residual distribution
was collected and no bands were derived.

## RPC duties and cost

15 launches, three cheap survivors and three deep candidates. Only three RPC
getAccountInfo bootstrap reads were sent: **one reserve read per selected
candidate**, 0.2 per launch; 12/15 launches required no deep read. Two reconciliations
succeeded (66.67%); one could not reconcile behind live tracked state and failed
closed. Successful reads remain identity-INCOMPLETE. This is a partial reserve
bootstrap cost, not the final cost of complete canonical/config verification.

| Duty | Actual reads |
|---|---:|
| Candidate reserve bootstrap | 3 |
| Periodic | 0 |
| Divergence repairs during passive pilot | 0 |
| Pre-entry | 0 |
| Exit | 0 |
| Offline investigation of uncached historical slots | 5 |

Total new RPC work: eight reads; two additional official-IDL documentation GETs.
There was no per-event polling. Production PumpSwap full pool/vault refresh needs
two RPC methods; Pump.fun reserve refresh needs one. Complete fee/identity bootstrap
has additional unmeasured duties. Periodic and event-count intervals remain unset.
Repairs are coalesced and admission/budget controlled; random-launch repair polling
is not enabled. Open exposure retains active RPC/fallback exit monitoring.

## Regression and readiness

Regression covers POST semantics, actual-transfer buy/sell reconstruction, missing
transfer, multi-event UNKNOWN, exact same-transaction order, missing mutation,
slot regression, identity/config mismatch, RPC recovery, mutation stack scoping,
invalid-state strategy rejection and emergency sell despite observational failure.
Full test/lint/type and read-only database results are recorded separately in
`analysis/production_state_verification.json`.

Ready for a larger **read-only synchronization acquisition**, with remaining
identity/config checks included as prerequisites to accepting calibrated evidence.
Not ready for percentage safety bands, complete local execution readiness or the
runner. Remaining blockers: incomplete mutation coverage and conservative global
invalidations; unknown log-only multi-event instruction state; unverified canonical
curve/pool/config identity; unsynchronized RPC residuals; unexplained new Pump.fun
mismatches and unlocated stream loss layer. Legacy PnL is not retroactively repaired.
