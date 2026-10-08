# API cost calibration — request cost measured; billing unresolved

Hard cap: 200 actual RPC requests, then stop. Method counts: {'getAccountInfo': 183, 'getSlot': 8, 'getMultipleAccounts': 9}.
Primary 196 / public exit 4. Native WSS: one connection, two subscription requests;
PumpPortal WSS: one connection, two FREE subscription requests. No metered trade events.
Four separately recorded official GitHub documentation GETs are outside trading-provider CU
billing. Browser documentation research is outside the calibration process.

Funnel: 22 distinct creations observed, 4 pool
creations, 8 local activity survivors, 8
paired tokens, 8 deeply inspected tokens, 180
pairs. Creations are deduplicated across streams. Pool creations are recorded separately;
not all pool creations are new tokens. Original capture did not retain the exact mint-set
intersection for a launch-only conversion: this rate is UNKNOWN. Mixed market survivors per
observed launch is 36.36%, which is not a launch-only conversion.
Filter-to-pair 100.00%. These tiny-window conversions
are biased estimates and cannot be used as representative monthly throughput.

Observed requests: 9.091/launch including shared
health/config probes; 25.000/candidate including
probes; 23.875 pairing reads/deep candidate;
1.061 pairing reads/pair including unsuccessful attempts.
CU/credit/currency charges are UNKNOWN, not zero: RPC responses provide no billing counters,
and native WSS notification CU accounting was not supplied. No billing-plan query or new API
purchase was made. PumpPortal discovery/migration stream charge is zero under its
[published schedule](https://pumpportal.fun/fees/); RPC/WSS plan costs remain unresolved.

Analytic request-only scenarios, NOT dollar forecasts: 1000 selected candidates with one pair
each require about 1000 Pump.fun reads or 2000 uncached PumpSwap reads, plus failures/probes.
100 serious candidates with ten pairs each have the same nominal request totals. Cached pool
metadata can remove repeated PumpSwap pool reads, leaving one vault batch per pair; invalidate
on migration/config change. Add any independent reference subset explicitly to the budget.
Monthly currency cost cannot be estimated honestly from 41s without launch-volume, conversion,
sampling policy, venue mix and method/CU billing inputs. Machine projections are null, with
request-count scenarios and formula retained.

Calls avoided: account reads for every new/unknown token; RPC transaction lookup per trade;
separate buy/sell quote-provider calls; FX calls for SOL-unit research; repeated supply/fee
config fetching; optional price APIs; all order-building/submission calls. Event decoding,
trade amounts, reserve marks, token age and local activity/volatility can be calculated locally.
Cache immutable market identities and versioned config; fresh reserves and exit recovery still
need timely observations. The first pilot over-sampled eight hot tokens; fair per-market
quotas/throttling should improve coverage before authorizing a larger metered capture.
