# Two worst trades — causal forensics

Research date: 1 October 2026 (Europe/Dublin). Historical timestamps below are UTC. Production configuration, thresholds and trading state were not changed.

## FLETCH — 8rNH5EtfpCQ9yomKWcuksxnRGf2ksyqoQeMjyCaJpump

Position `bbd44070-9df0-4ca5-a555-bff6af56c792`. Net -15.42809836 USDT / -60.85%. Quality MEDIUM; 8 in-position trade ticks.

| T+seconds | UTC timestamp | Stage | Price raw if retained |
|---|---|---|---|
| 0.000 | 2026-09-16T21:20:47.986118+00:00 | discovery | — |
| 14.710 | 2026-09-16T21:21:02.696446+00:00 | buy:signal_at | — |
| 16.345 | 2026-09-16T21:21:04.330971+00:00 | buy:decision_at | — |
| 16.395 | 2026-09-16T21:21:04.380971+00:00 | buy:submitted_at | — |
| 17.262 | 2026-09-16T21:21:05.248199+00:00 | buy:filled_at | 0.00007641507944594547228095499562 |
| 18.722 | 2026-09-16T21:21:06.708395+00:00 | observed_MFE | 7.866018441058038e-05 |
| 19.496 | 2026-09-16T21:21:07.482500+00:00 | sell:signal_at | — |
| 19.658 | 2026-09-16T21:21:07.643994+00:00 | sell:decision_at | — |
| 20.402 | 2026-09-16T21:21:08.387888+00:00 | observed_MAE | 3.950308354163182e-05 |
| 20.555 | 2026-09-16T21:21:08.540703+00:00 | sell:filled_at | 0.00003064797510047343342857650272 |

Entered because Aggressive emitted `early_demand` and score 66.88 exceeded 55. Risk allowed=true, score=8.96, completeness=89.47%, no hard rejects. Components: momentum=65.06 (weight 70), wallet=None (weight 0), risk=91.04 (weight 0), social=None (weight 0), lifecycle=85 (weight 0), market=0 (weight 0), graduation_velocity=71.14 (weight 30).

| 10-second entry-window metric | Recorded value |
|---|---|
| buy_count | 26 |
| sell_count | 11 |
| unique_buyers | 26 |
| buy_volume_quote_raw | 15132571055 |
| sell_volume_quote_raw | 9587593117 |
| buy_sell_volume_ratio | 1.578349317741494640442614436 |
| price_velocity_percent_per_second | 3.216089900148583014737229485 |
| price_acceleration_percent_per_second2 | -0.1524737942195078423977875404 |
| volume_velocity_quote_raw_per_second | 2472016417.2 |
| volume_acceleration_quote_raw_per_second2 | 159998501.84 |
| unique_buyer_rate_acceleration_per_second2 | 0.32 |
| largest_buy_quote_raw | 1466666665 |
| largest_sell_quote_raw | 3799513523 |
| latest_price_return_percent | -9.610672696596240202175433358 |
| latest_sell_liquidity_fraction | 0.1389097157072468026625065813 |

Top-1 / top-10 holders: 12.5474% / 61.1947%; creator holding snapshot 0.0000%. This is not evidence that creator never sold. Funding/insider graph, organic score, smart-wallet participation and time-series holder growth are UNKNOWN.

First trade was 3.395s after discovery. Return from that first recorded price to entry mark: 61.73%; from the observed pre-entry low: 61.73%; from first structural momentum signal: 53.63%. Exact discovery-price return is UNKNOWN. Actual fill versus first recorded price: 67.46%. Signal→decision 1.635s; decision→fill 0.917s.

Recorded MFE / MAE 2.94% / -48.30%. Time to observed MFE 1.46s; time to recorded MAE 3.14s. RPC exit mark differs from the last available feed tick by -21.77%. The complete timeline retains this discrepancy; it is not interpolated away.

## cappuccinu — H1qib6bJJ2EUA61nwq8XuFfEZDq51HW9XKKey57Tpump

Position `19ac436f-d663-496b-bcc5-f969c27c4712`. Net -20.56507668 USDT / -67.08%. Quality LOW; 348 in-position trade ticks.

| T+seconds | UTC timestamp | Stage | Price raw if retained |
|---|---|---|---|
| 0.000 | 2026-09-17T12:43:08.103027+00:00 | discovery | — |
| 66.939 | 2026-09-17T12:44:15.041792+00:00 | buy:signal_at | — |
| 69.096 | 2026-09-17T12:44:17.199019+00:00 | buy:decision_at | — |
| 69.146 | 2026-09-17T12:44:17.249019+00:00 | buy:submitted_at | — |
| 70.307 | 2026-09-17T12:44:18.410081+00:00 | buy:filled_at | 0.00009599807453395956034184193875 |
| 71.110 | 2026-09-17T12:44:19.213149+00:00 | observed_MAE | 9.423275411304371e-05 |
| 1852.672 | 2026-09-17T13:14:00.775054+00:00 | observed_MFE | 0.00014779502649159976 |
| 2233.751 | 2026-09-17T13:20:21.853921+00:00 | sell:signal_at | — |
| 2234.102 | 2026-09-17T13:20:22.205415+00:00 | sell:decision_at | — |
| 2235.219 | 2026-09-17T13:20:23.322330+00:00 | sell:filled_at | 0.00003248672046829802304284009804 |

Entered because Aggressive emitted `early_demand` and score 67.52 exceeded 55. Risk allowed=true, score=15.79, completeness=89.47%, no hard rejects. Components: momentum=66.09 (weight 70), wallet=None (weight 0), risk=84.21 (weight 0), social=None (weight 0), lifecycle=85 (weight 0), market=0 (weight 0), graduation_velocity=70.87 (weight 30).

| 10-second entry-window metric | Recorded value |
|---|---|
| buy_count | 3 |
| sell_count | 2 |
| unique_buyers | 3 |
| buy_volume_quote_raw | 366256242 |
| sell_volume_quote_raw | 33063607 |
| buy_sell_volume_ratio | 11.07732262847184216773445196 |
| price_velocity_percent_per_second | 0.1483915615948645853119315983 |
| price_acceleration_percent_per_second2 | 0.00257243423837358146655455956 |
| volume_velocity_quote_raw_per_second | 39931984.9 |
| volume_acceleration_quote_raw_per_second2 | 1957640.6 |
| unique_buyer_rate_acceleration_per_second2 | 0.04 |
| largest_buy_quote_raw | 142125810 |
| largest_sell_quote_raw | 28183624 |
| latest_price_return_percent | 0.4234728602579462249205060359 |
| latest_sell_liquidity_fraction | None |

Top-1 / top-10 holders: 22.1074% / 60.0230%; creator holding snapshot 0.0000%. This is not evidence that creator never sold. Funding/insider graph, organic score, smart-wallet participation and time-series holder growth are UNKNOWN.

First trade was 0.742s after discovery. Return from that first recorded price to entry mark: -21.07%; from the observed pre-entry low: 13.19%; from first structural momentum signal: -21.20%. Exact discovery-price return is UNKNOWN. Actual fill versus first recorded price: -19.24%. Signal→decision 2.157s; decision→fill 1.211s.

Recorded MFE / MAE 53.96% / -33.18%. Time to observed MFE 1782.36s; time to recorded MAE UNKNOWNs. RPC exit mark differs from the last available feed tick by -73.33%. The complete timeline retains this discrepancy; it is not interpolated away.

## Broader-window evidence available at entry

FLETCH: saved 60s-window buy/sell volume ratio 1.988467792127980028791500406; buyer acceleration 0.0388888888888888888888888889; volume acceleration 32164197.59555555555555555556. Observed creator-address sells during the position: 0. Zero observed creator sells cannot rule out linked-wallet dumping.

cappuccinu: saved 60s-window buy/sell volume ratio 0.9867362742055435627406073003; buyer acceleration -0.02555555555555555555555555555; volume acceleration -58595193.82777777777777777777. Observed creator-address sells during the position: 0. Zero observed creator sells cannot rule out linked-wallet dumping.

All recorded entry windows, risk evidence and score components are retained in `analysis/worst_entry_evidence.json`. Broader-window disagreement motivates an ablation; it does not establish a reject rule.



## Failure classification and rejection feasibility

FLETCH: **observed overextension, sell shock, rapid reversal and tail loss**. Its linked entry feature already showed -9.61% on the latest trade, a 2.48 SOL sell, 13.89% of reported real quote liquidity and a 13.64 MAD sell-size score. The snapshot preceded decision/fill. Rejection on a sell-shock hypothesis was mechanically possible without future information. This flag appears in only one losing entry and no winning entries among 215 available entry snapshots: insufficient to estimate its true benefit. Creator dump, insider dump and rug attribution are **INSUFFICIENT EVIDENCE**. A stop signal existed; calling this NO_EXIT_SIGNAL would be wrong. A 3.29-second crash also limits how much an exit can avoid.

Cappuccinu: **profit giveback, feed/RPC disagreement, coverage gaps and tail loss**. It entered -21.07% below its first observed price, not after the same kind of initial chase. Its entry's last 10 seconds had five trades/three buyers and strong buy-volume imbalance; short-window evidence looked favorable despite weak broader flow. A negative earlier episode is not proof of failure at this entry. Observed MFE took 1,782s after entry. The final feed gap reached 268.81s, and the RPC exit mark was 73.33% below the latest feed tick. Recorded MAE cannot be timestamped from these ticks. Holding/exit quality deserves investigation, but a reliably executable earlier exit price or a pre-entry rejection rule is **INSUFFICIENT EVIDENCE**.

The two losses total 35.99317504 USDT: 81.19% of net experiment loss, but 75.64% of **gross losing-position amounts**. Denominators are different. Both exits were stop_loss. Do not infer a new TP/SL optimum from two trades.

The complete CSV/JSON timeline includes every retained 10-second feature snapshot, profile decision, signal, submission, fill, RPC reserve time and SOL/USD reference time. T+1/T+2 fields remain unknown where no event exists. `risk_snapshot_causal_at_this_time=false` means a linked risk assessment arrived later; it was not known at that observation. Market cap assumes 1B six-decimal Pump tokens; liquidity is real SOL quote reserves, not a liquidity valuation. Research phases are annotations, not historical production states.


Reproduction: see [DATA_QUALITY.md](DATA_QUALITY.md). Machine-readable JSON and CSV are in `analysis/`.