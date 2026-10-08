# Stream proof cost — bounded pilot

The 300-second/96-read/4-candidate pilot stopped at its 32 MB application-data cap.
Total runtime was 22.479 seconds, including setup and connection teardown.
It received 32,006,935 decoded application bytes, 16,530 log notifications,
43 slot updates, 0 account updates and zero complete transactions.
One serious natural standard candidate generated one OLD and one NEW proof attempt.
Each used one RPC read and failed physical reconstruction. Successful-proof cost is undefined.
OLD latency was [263.25409999117255]; NEW was [59.766000136733055] ms.
This failed early, so the one-read result is not the cost of complete proof.

The local historical BUY and SELL regression replays each use five proof RPC reads,
then one mandatory execution refresh: six total versus seven in the old single-anchor
model. One captured transaction saves one historical transaction read. The four
address-history fences and fresh account bank remain. The intended stream plus one
refresh model has not been demonstrated.

Measured application throughput over total runtime is 1,423,853 bytes/sec;
85,431,202 bytes/minute and 32,006,935 bytes/serious candidate.
Compressed, TLS/wire and actual provider-billed bytes are unavailable.
The sample includes all Pump/Fee log traffic before cheap standard-only eligibility
filtering. Excluded markets caused no candidate proof reads, but still consume feed
bandwidth. These costs cannot be attributed exclusively to eligible standard tokens.

| Horizon | Projected application bytes | Paired pilot RPC reads |
| --- | ---: | ---: |
| 1_hour | 5,125,872,128 | 320 |
| 24_hours | 123,020,931,061 | 7,687 |
| 30_days | 3,690,627,931,828 | 230,614 |

Projections assume the short observed workload, candidate rate and subscriptions
remain constant, with setup/teardown included. They are usage scenarios, not forecasts.
Full transaction/account packets have different size and filtering requirements;
this pilot supplies no defensible numeric projection for them. Actual account plan,
included credits and metered bytes are unknown, so actual dollar cost is UNKNOWN.
Published rates and plan sources are in STREAM_PROVIDER_COMPARISON.md; no service
was purchased, upgraded or enabled. See analysis/stream_provider_cost.json for units.
