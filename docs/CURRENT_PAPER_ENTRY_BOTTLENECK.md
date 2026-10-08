# Current PAPER entry bottleneck audit

Experiment: `standard-pump-operational-paper-20261002-214954`. Snapshot window: 2026-10-02T22:49:54.778288+01:00 to 2026-10-03T00:18:41.817070+01:00 (Europe/Dublin). Duration: 88.8 minutes.

Read-only investigation. The running worker, entry thresholds, model, and controls were not changed or paused. Counts are a bounded snapshot; the bot continues running.

## Finding

The most frequent pre-qualification category is deterministic risk rejection. Once the strategy and local model approve an entry, the dominant actual execution blocker is signal expiry: eight of nine approved buys fail the 25-second signal-age check. The zero-trade conclusion of the earlier 15-minute experiment does not describe this longer run: the model has now approved buys and one buy/sell cycle completed.

| Funnel stage | Decisions |
|---|---:|
| Active strategy decisions | 405 |
| Deterministic skips | 356 |
| Watch only | 3 |
| Deterministic entry-qualified; sent to local policy | 46 |
| Local policy explicit veto | 25 |
| Local policy unavailable/invalid response | 12 |
| Local policy buy approval | 9 |
| Buy execution rejected | 8 |
| Filled buys | 1 |
| Filled sells | 1 |

Distinct risk-assessed candidate coins: 157. Approved entries involve 5 distinct coins. Counts of decisions are not counts of launches or independent opportunities.

## Deterministic rejections

Counts overlap: one decision can have several reasons. They cannot be added as disjoint rejection stages.

| Category | Decisions with category | Decisions with only this category |
|---|---:|---:|
| risk | 220 | 39 |
| observation_span | 189 | 24 |
| buyer_concentration | 181 | 3 |
| trade_count | 172 | 3 |
| buyer_count | 139 | 0 |
| buy_flow | 101 | 23 |
| buyer_attribution | 4 | 0 |
| score | 1 | 1 |
| token_age | 1 | 0 |

Hard concentration reasons: largest-holder threshold >=35% appears in 178 decisions; creator-holding threshold >=20% in 76 decisions. Missing risk data also prevents approval. The exclusive-category count is not a promise of an additional trade: score, local policy, and execution would still need to pass.

## Approved-entry expiry evidence

Seven buys have `entry_signal_expired`; one has `entry_signal_expired_before_fill`. Every recorded buy execution rejection in this snapshot is expiry. No market-cap, price-impact, fee, portfolio-capacity, or canonical-state rejection was recorded for these nine approved buys.

| Mint prefix | Outcome | Signal age before model, s | Local receipt delay, s | Decision-to-order, s | Signal age at order, s |
|---|---|---:|---:|---:|---:|
| MKyr6GyN | entry_signal_expired | 40.58 | 39.99 | 8.94 | 49.53 |
| MKyr6GyN | entry_signal_expired | 21.44 | 20.78 | 7.28 | 28.72 |
| MKyr6GyN | entry_signal_expired | 29.81 | 29.27 | 6.22 | 36.03 |
| MKyr6GyN | entry_signal_expired | 22.70 | 22.01 | 7.92 | 30.63 |
| 8SMrBtkY | entry_signal_expired | 20.44 | 19.95 | 7.64 | 28.08 |
| 2eNvz3dc | entry_signal_expired | 19.02 | 18.38 | 7.79 | 26.81 |
| 8podTmMw | entry_signal_expired_before_fill | 20.32 | 19.76 | 5.59 | 25.91 |
| 8podTmMw | entry_signal_expired | 31.79 | 31.36 | 2.58 | 34.37 |
| 8FmVdmPy | filled | 14.54 | 13.99 | 4.85 | 19.39 |

Across 6180 standard non-Mayhem Pump.fun trade events, source-to-local-processing receipt delay is p50 20.32s, p95 34.34s, maximum 47.32s. 2153 events (34.8%) already exceed 25 seconds at receipt. Estimated source timestamps were excluded; this snapshot has none.

The decision timestamp is inherited from collected risk facts before the model request. Decision-to-order time includes local inference, queueing and execution preparation. It is not an isolated measurement of model inference. Recorded risk fact collection completes roughly 0.4–0.7 seconds after local receipt for these approved buys; the large initial delay predates it.

The native provider receive loop awaits notification normalization and publication. EventBus awaits handlers, including persistence and downstream work. This permits local receive backlog. The stored timestamps cannot prove how much delay is upstream provider delivery versus local backlog; assigning all delay to the provider or Ollama would overclaim.

All nine approved decisions have unavailable observational latest price in the retained feature snapshot. Exact current execution price is separately refreshed; missing observation price can also affect discretionary vetoes and scoring quality. It is not listed as the direct execution rejection of these buys.

## Current status and next fix

Entries paused: False. Open positions: 0. One position closed with realized PnL -4.73272506 in portfolio currency. No profitability inference is justified by one trade.

The next concrete fix should target acquisition/processing age and revalidate against fresh observed features before an approved order. Preserve the final atomic refresh and stale-signal protection. Increasing the 25-second limit alone would admit older evidence rather than resolve the demonstrated delay. Local-policy vetoes and its 12 failures are an additional earlier bottleneck, but this audit cannot classify those failures further without retained error logs.

Machine evidence: analysis/current_paper_funnel_audit.json; analysis/current_paper_entry_timing.json; analysis/current_paper_feed_delay.json.
