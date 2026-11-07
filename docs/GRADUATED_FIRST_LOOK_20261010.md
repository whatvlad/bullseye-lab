# Graduated coins (PumpSwap): first look — 2026-10-10

> **Correction (same day):** the numbers below were inflated. 54 of the 84 "graduated" pools were
> not real graduations (25 dust pools with < 2 SOL whose price jumped 10× on tiny trades, plus
> older/large pools), and entries used the reserves *before* the triggering trade. On the **31 real
> graduation pools** (opening with 50–100 SOL), using prices *after* each trade, the rule
> "buy at graduation, +30% / −15%" gives **+6.7% per trade (95% range −1.3% to +14.9%), 50%
> winners**. Buying 30 s later is already negative. Promising but unproven; paper trading
> (`pumpswap_recorder.py --paper`, real pools only) is the forward test.

Research only, no code or settings changed. Script: `analysis/dataset/pumpswap_first_look.py`
(data: `analysis/pumpswap/*.jsonl` from `analysis/pumpswap_recorder.py`).

## Data

- 295,154 PumpSwap trades on 126 graduated coins, recorded 2026-10-09 12:32 → 10-10 00:25 UTC.
- Used: the **84 coins** first seen ≤ 60 s after graduation. Price = pool quote / base reserves
  from each trade event.

## Fees (measured live, 10 s probe of PumpSwap buy/sell events)

| Pool size | LP | Protocol | Creator | Total per side |
|---|---:|---:|---:|---:|
| Fresh graduate (< 120 SOL) | 0.02% | 0.93% | 0.30% | **1.25%** |
| 120–300 SOL | 0.20% | 0.05% | 0.80–0.95% | 1.05–1.20% |
| Large pools (≥ 300 SOL) | 0.20–0.25% | 0.05% | 0–0.65% | 0.30–0.90% |

So fresh graduates are **not** cheaper than the bonding curve (my earlier "0.3%" was wrong for
them). Replay cost used: 1.85% per side (1.25% fees + ~0.6% slippage/priority), latency 0.8 s.

## Results (one buy per coin, 84 coins)

| Buy at | Exit | Winners | Mean | Median |
|---|---|---:|---:|---:|
| **graduation (0 s)** | **+30% take-profit / −15% stop** | **57%** | **+15.6%** | **+20.2%** |
| graduation (0 s) | current rules | 44% | +31.4% | −4.2% |
| graduation (0 s) | +100% / −30% | 45% | +21.5% | −3.7% |
| graduation (0 s) | hold 30 min | 25% | −42.5% | −89.5% |
| +30 s | +30% / −15% | 46% | −2.0% | −3.4% |
| +60 s | +30% / −15% | 47% | +2.7% | −1.8% |
| +2 min | +30% / −15% | 47% | −1.4% | −1.2% |
| +5 min | +30% / −15% | 33% | −13.0% | −14.0% |

Robustness of "buy at graduation, +30% / −15%":

- Latency 0.8 / 1.5 / 3 / 5 / 10 s → mean +15.6 / +13.4 / +4.9 / +6.6 / +4.9%.
- Costs 1.85 / 2.5 / 3.0% per side → +15.6 / +14.0 / +12.6%.
- First vs second half of the coins (by time) → +20.4% / +10.8%.
- Simple filters at +2 min (price up/down, net buying/selling) don't separate outcomes.

## Caveats (why this is not proof yet)

- **84 coins from one evening/night.** One regime; the rule was picked after looking at the data.
- 15–16 positions ran past the recorded data (recorder's hourly cap) and are marked at the last
  price.
- Fills use the price of the first recorded trade after the latency; real fills in the first
  seconds after migration compete with snipers.
- Holding is terrible: most graduates dump within 30 min (median −89%).

## Next step

Freeze the rule exactly as above (buy at graduation, sell at +30% or −15%) and re-run it on the
**next ~100 coins only** (recorded after 2026-10-10 00:25 UTC). If it stays clearly positive,
build paper trading for graduated coins (off by default) and run it at 0.1 SOL.
