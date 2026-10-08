# Loss analysis — 1 October 2026

Source: fresh read-only PostgreSQL snapshot, reproduced by `python -m memebot.research.capture` and `python -m memebot.research.forensics`. Detailed per-portfolio and outcome statistics are in [loss-statistics-2026-10-01.json](loss-statistics-2026-10-01.json). The database contains 225 positions but 215 trade outcomes; ten early positions lack outcome records. Portfolio-ledger results include those positions; excursion/feature segments use only recorded outcomes. Portfolio names are not unique, so reports key by portfolio ID.

## Latest experiment

`sniper-v9-forward-2026-09-13`, portfolio `711ce8d0-76a8-43f9-83ec-3681b8e63fcb`:

| Measure | Result |
|---|---:|
| Closed positions / wins / losses | 10 / 3 / 7 |
| Initial cash / remaining cash | 100 / 55.66645606 USDT |
| Net realized PnL | −44.33354395 USDT |
| Win rate | 30% |
| Mean win / mean loss magnitude | 1.08417 / 6.79801 USDT |
| Median win / median loss magnitude | 0.47733 / 2.65163 USDT |
| Net expectancy | −4.43335 USDT per position |
| Profit factor | 0.06835 |
| Recorded fill fees, both sides | 7.22566 USDT |
| Net PnL with largest winner removed | −46.65825 USDT |
| Closed-position realized drawdown | 44.33354 USDT |
| Cash/cost/realized reconciliation difference | 0.00000001 USDT |
| Decision-to-fill p50 / p95 / p99 (22 orders) | 951.924 / 1250.021 / 1277.107 ms |

EV = 0.30 × 1.08417 − 0.70 × 6.79801 = −4.43335 USDT. Net results already include recorded execution costs. Do not subtract the 7.22566 USDT again. Adding those costs back gives approximately −37.10788 USDT, so fees alone cannot explain this loss. That remainder still includes modeled slippage and price impact: it is **not** a clean estimate of signal-only loss.

## What can be attributed

- **Price movement / exposure:** the two largest losses were −15.42810 and −20.56508 USDT, roughly 81% of the net loss together. The first position lasted three seconds. A 12% stop is a trigger and cannot guarantee a 12% fill during a gap/crash. Earlier 30–40% sizing increased the capital damage.
- **Profit retention:** recorded MFE of +544% and +647% ended with +2.32471 and +0.45047 USDT after partial exits and reversals. This motivates exit research, not an invented optimum TP.
- **Infrastructure:** stored gaps include a 269-second trade interval for a large losing position. PumpPortal now reports an unfunded trade stream. Historical RPC/WSS failures are numerous. Causal attribution of a particular loss to a provider is unproven.
- **Accounting:** latest portfolio reconciles within eight-decimal ledger rounding. The newly repaired incomplete CLOSE defect is a reproducible vulnerability, not proven to have occurred in these ten trades.
- **Execution:** paper fees, impact and slippage are explicit assumptions. There are no real signed buys/sells, transaction confirmations, priority-fee samples or Jito costs to audit. A live fee/slippage attribution cannot be manufactured.
- **Strategy:** observed net expectancy is negative. Version/sizing changes and small samples prevent identifying a stable strategy edge or attributing all losses to one feature.
- **Model:** emergency-stop and risk-veto bypasses existed in current code. The available historical evidence does not establish that Ollama caused the September losses.

## Historical experiments (different runs, not an A/B ranking)

| Run | Trades | Net USDT | EV USDT | Profit factor |
|---|---:|---:|---:|---:|
| baseline-v1 | 22 | +3.97941 | +0.18088 | 1.47436 |
| baseline-v2 | 60 | −11.59364 | −0.19323 | 0.63841 |
| baseline-v3-fixed | 8 | +1.82990 | +0.22874 | 1.53853 |
| baseline-v4 | 13 | −16.75062 | −1.28851 | 0.44814 |
| baseline-v5-fixed | 35 | −4.07688 | −0.11648 | 0.82516 |

The JSON report covers every portfolio, including early manual portfolios. It reports means, medians, realized drawdown, fees, reconciliation, missing evidence, and outcome segments by strategy, exit reason, entry hour and runner-score bucket. Excursion distributions use recorded marks, exclude missing values and preserve their limited coverage. Full intratrade executable MAE/MFE, liquidity/age/risk/latency/source buckets and causal earlier/later entry experiments require complete reserve and conversion-price histories. They are not inferred from chart highs.

Loss labels such as rug, insider dump, fake smart wallet, stale quote or failed real sell remain **unknown** absent corresponding evidence. Stop-loss exit labels do not prove an entry cause. No TP/SL values were optimized from this sample.
