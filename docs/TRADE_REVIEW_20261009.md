# Trade review and strategy assessment — 2026-10-09

Read-only analysis. No code or settings were changed. All numbers come from the local
Postgres (`trade_outcomes`, `decision_outcomes`, `token_trades`) unless a source link is given.

## 1. Short answer

- **The bot loses money on its own.** Since the Oct 8 fixes, 60 paper trades: 23% winners,
  −224 USDT in total. The 55 automatic exits lost **−417 USDT**. The 5 positions you sold
  by hand made **+192 USDT**.
- **The problem is the entry, not the exits.** I replayed every buy candidate since Oct 8
  (195 tokens) against the recorded trade prints. No exit rule I tried (stop 10–50%, take
  profit at +30/+50/+100%, break-even stop, no stagnation exit, time exits) turns the result
  positive. The best is still about −3% to −6% per trade.
- **Why:** the strategy buys a 10-second price spike. By the time we fill (≈0.8 s later, plus
  ≈2.25% fees and slippage per side), the spike is usually over. 42% of trades were never
  in profit at all.
- **Size is inverted.** Higher scores get bigger sizes (0.5 SOL at 70–85), but score 70+
  trades did *worse* (11–14% winners) than score 60–70 (45% winners). The 0.3–0.5 SOL
  trades produced −244 USDT, most of the loss.

## 2. Trades since the Oct 8 fixes (n = 60)

| Exit | Trades | Winners | P&L (USDT) | Avg loss | Median hold |
|---|---:|---:|---:|---:|---:|
| Stop-loss | 39 | 1 | −602 | −36% | 42 s |
| Trailing stop | 9 | 9 | +218 | — | 4.6 min |
| Stagnation (2 min) | 7 | 0 | −33 | −10% | 2 min |
| Manual sell (you) | 5 | 4 | +192 | — | 14 min |

- **Stop-loss is set at 15%, but stops fill at −36% on average.** 9 trades lost 65–86% in
  one step (single-block dumps or a dead curve). Those 9 trades are −342 USDT, more than half
  of all losses. No stop level can catch a dump that happens inside one block; only an entry
  filter can avoid them.
- 16 of the 39 stops fired within 30 s of the buy. That means we bought the top of the spike.
- 7 stopped tokens later went above +50% from our entry. That shows how noisy these coins are;
  it does not mean a wider stop helps (see §4).
- Fees were 1.76% of the position on entry (median), plus the same on exit, plus 0.5%
  simulated slippage each way. A trade has to rise ≈4.5% just to break even.

By score (all 60 trades):

| Score | Trades | Winners | Avg P&L |
|---|---:|---:|---:|
| 55–60 | 14 | 14% | −21.5% |
| 60–70 | 20 | 45% | +25.0% |
| 70–80 | 19 | 11% | −22.6% |
| 80+ | 7 | 14% | −13.6% |

The 60–70 band looks better partly because three of your big manual sells sit there. On the larger replay
(§3) no score band is clearly positive. The score does not predict outcome.

Earlier runs (Aug 23 – Oct 7, 237 trades, older price model) were also negative: 30%
winners, median −10.6%. Prices before Oct 8 are not reliable, so I don't use them further.

## 3. Replay of all buy candidates (n = 195) and a random baseline (n = 2,010)

Method: for each token's first `enter_candidate` decision since Oct 8, take the recorded trades
for 30 min. Buy at the first trade ≥0.8 s after the decision, apply 2.25% cost per side,
run the current exit rules on every later trade, and sell at the first trade ≥0.8 s after
the exit fires. Script: scratchpad `sim.py` (I can commit it as `analysis/replay_exits.py`).

| Variant | Trades | Winners | Mean per trade |
|---|---:|---:|---:|
| **Current rules** | 195 | 22% | **−8.4%** |
| Same rules on random tokens at first sight (skips) | 2,010 | 8% | −5.9% |
| Current rules, zero fees | 195 | 26% | −5.9% |
| Current rules, zero latency | 195 | 22% | −3.0% |
| Wait 10 s, buy only if price ≥ decision price | 103 | 30% | −2.9% |

The candidates do slightly *worse* than random tokens: the signal has no edge after costs.
The replay is in line with reality: real automatic trades did even worse (−15% average).

Exit variants (all on the same 195 candidates):

| Change | Mean per trade |
|---|---:|
| Stop 10% / 15% (now) / 25% / 50% | −6.2% / −8.4% / −10.0% / −12.4% |
| No stagnation exit | −7.5% |
| Break-even stop after +20% | −8.3% |
| Partial take-profit 50% at +30% | −9.2% |
| Sell everything at +50% | −10.0% |
| No stop, sell at +100% or after 10 min | −8.8% |

Wider stops lose more. Exits can only change how fast we lose.

Feature buckets on the 195 replays (token age, bonding progress, 10/60/300 s price change,
buyers, largest-buyer share, sells): nothing holds up. A few buckets are slightly positive
(token age > 15 min: +13%, n = 10; progress 60–80%: −0.2%, n = 50), but the samples are too
small to trust.

**Following profitable wallets:** I scored 15,246 wallets on trades *before* Oct 8 and checked
whether "smart" wallets (≥5 tokens, ≥ +0.5 SOL net, ≥50% winners) buying in the 2 min before a
decision helps afterwards. It doesn't. Among candidates: −8.3% with them vs −8.6% without. Among
random tokens it is worse with them (−8.6% vs −4.4%). Many "profitable" wallets are snipers who
sell to the people who follow them.

## 4. What the outside research says

- Only about 0.2–0.6% of Pump.fun tokens graduate, and most die within minutes
  ([arXiv 2607.02823](https://arxiv.org/abs/2607.02823),
  [madeonsol](https://madeonsol.com/blog/pump-fun-first-3-minutes-graduation-math)).
- In one month of data (655k tokens), at least one pump-and-dump showed up in **92%** of tokens
  with ≥30 swaps, mostly mid-curve. Buy-and-hold is profitable only if
  P(graduate) > (SOL in curve / 115)². The plain curve-level probability stays below that line.
  The strongest predictor of graduation was **trading speed** (reaching a SOL level in fewer
  trades). The paper does not show a profitable strategy, and it ignores fees
  ([arXiv 2602.14860](https://arxiv.org/html/2602.14860v1)).
- Deployer-funded snipers took 15,000+ SOL in one month, with 87% of snipes profitable. 55% of
  them were out within 1 minute and 85% within 5 minutes. That is exactly the window our 10 s
  momentum entry buys into
  ([Pine Analytics](https://pineanalytics.substack.com/p/exit-liquidity-machines)).
- Industry claims: sniper bots profit mainly from latency (<50 ms RPC), and only ~10% are
  consistently profitable. Late chases (minute 5+) and random entries are negative EV. These
  are vendor claims, not verified
  ([rpcfast](https://rpcfast.com/blog/how-to-launches-snipe-pump),
  [madeonsol](https://madeonsol.com/blog/pump-fun-first-3-minutes-graduation-math)).
- Copy-trading guides agree the edge must be proven net of lag and fees; none show it
  ([madeonsol copy-trading](https://madeonsol.com/blog/how-to-copy-trade-on-solana)).

My reading: a 0.8 s, logs-based paper bot can't win the first-minute speed race against
deployer-linked snipers. Any edge has to come from **avoiding** the dumps (entry filters) or
from a **slower setup** where speed matters less. Both have to be proven in replay before
they get real weight.

## 5. Proposals (in order; each is your call)

1. **Size flat at 0.1 SOL until an entry shows positive replay EV.** Today's tiers give the most
   money to the worst-performing scores. The ≥85 "whole portfolio" tier would turn one dump into
   −75–86% of the account. This lowers risk; it does not loosen any filter.
2. **Commit the replay tool** (`analysis/replay_exits.py`) and make it the gate. No entry or exit
   change goes live unless replay on the latest data is positive after costs and latency.
3. **Shadow-log three entry ideas (flag-only, no effect on buying)**, then backtest after a few
   days and you pick:
   - **10 s confirmation:** price 10 s after the signal is still ≥ the signal price.
     Best replay so far (−2.9%, 103 trades). It cuts trades, which tightens entries.
   - **Trading speed:** SOL added to the curve per trade, from the arXiv paper's strongest
     predictor. Needs one new feature.
   - **Holder concentration:** 5+ holders each ≥3% (from the insider backtest: 4 losers,
     0 winners). Already logged as `insider_facts`.
4. **Leave the exits alone for now.** Every tested exit change is small or negative while the
   entry has no edge. Revisit once an entry passes step 3.
5. **Don't pursue copy-trading wallets** in its simple form (tested above, no edge).

## 6. What is unverified

- Real paper sample is small (60). Replay is larger (195) but uses fixed costs (2.25% per side)
  and a fixed 0.8 s latency. It also ignores price impact of our own buy, which makes real
  results a bit worse than replay.
- 22 replays ended because the bot was switched off (data stops). They are marked at the last
  price.
- 900 s horizons are empty in `decision_outcomes`, and 60/120 s horizons have gaps.
- Wallet scores only count trades the bot saw (candidate tokens while it was running). Unsold
  tokens count as losses.
- Two or three more days of running with the current settings would double the replay sample.
