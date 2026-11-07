# Insider / holder backtest — 2026-10-08

31 closed paper positions since 17:50 UTC. Holders were rebuilt **as of the moment of
entry** from stored trades (net buys − sells per wallet, % of the 1B supply, bonding
curve excluded). Funders were resolved now via RPC for 534 holder wallets (funding
history does not change). "worst" = lowest price within 30 min after entry vs the buy.

Columns: `n>X%` holders with at least X% · `top10%` · `linked%` supply held by holders
sharing a non-hub funder · `fresh%` supply held by wallets whose first transaction was
<24 h before entry · `devsold` creator sold before entry · `dev%` creator holding ·
`launch/grad` creator wallet's launches/graduations seen by this bot.

```
token            pnl  worst n>1% n>2% n>3% n>5% top10% linked% clust fresh% devsold  dev% launch/grad
NOV19        -109.79    -87   20    7    2    1   28.0     0.0     0    0.0   False   2.8         1/0
bunk          -90.49    -85   15   15   15    0   42.4     4.3     1    0.2   False   0.0         1/0
MEMELIFE       -8.85    -80   20    9    5    1   29.6     0.0     0    0.0    True   0.0         1/0
TOLYGENT      -14.64    -79   20    5    2    0   23.7     0.0     0    3.5   False   3.5         1/0
qSol           19.72    -78   20    2    0    0   18.7     0.0     0    0.0    True   0.3         1/0
XYNR          -13.14    -78   20    4    2    0   21.6     0.0     0    1.2    True   0.0         1/0
DEGENS        -42.29    -77   19    9    3    0   26.0     0.0     0    2.2    True   0.0         1/0
BARKET         -3.26    -70   13    8    4    1   37.2     6.3     1   15.4   False   0.9         1/0
TRIBUTE        -1.68    -69   19   10    6    2   35.5     0.0     0   14.2   False   5.7         1/0
PUMP           15.28    -63   17    3    2    0   20.8     0.0     0    0.0    True   0.0         1/0
DIRECT         -7.63    -58   19    1    1    0   19.5     0.0     0    3.4   False   3.4         1/0
DOCAGENT      -11.33    -54    9    5    4    1   29.2     0.0     0    0.0    True   0.0         1/0
Quantum       -12.30    -45   20    8    0    0   23.8     0.0     0    0.0   False   0.0         1/0
UNFOLD        -20.42    -43   10    7    2    0   25.3     7.3     1   10.7   False   3.4         1/0
GROKPAD       -18.30    -41    6    5    3    0   21.6     8.2     1    7.5   False   3.4         1/0
SIF           -20.17    -40    9    2    2    2   22.3     0.0     0    1.0   False   1.0         1/0
WR             -3.41    -38   10    5    1    0   20.5     0.0     0    5.9    True   0.0         1/0
SYRUP          -4.99    -35    7    4    2    1   19.5     0.0     0   18.6   False   0.0         1/0
Console        10.18    -31    5    3    3    1   17.0     0.0     0    0.0   False   3.4         1/0
TENDRIL        -5.22    -22   20    7    1    0   22.6     0.0     0    0.0   False   2.0         1/0
SHNICK         -3.02    -22   20   10    4    1   31.4     7.3     1    7.3   False   5.5         1/0
QUIDD          -2.19    -21    8    8    8    0   33.6     0.0     0    3.4   False   0.0         1/0
xcoin          -1.37    -21    5    1    1    0   10.8     0.0     0    1.6    True   0.0         9/0
quntump        -7.19    -20    8    5    3    1   28.3     0.0     0    0.0    True   0.0         5/0
GAMBL         -21.92    -17    8    4    4    3   31.7     0.0     0    0.0   False   0.4         1/0
PF             31.28     -9   12    8    4    0   28.3     0.0     0    0.0   False   4.1         9/0
giftr          29.91     -7   20    2    1    0   21.0     0.0     0    4.4   False   4.4         1/0
step by ste   105.02     -4   20    8    3    0   29.2     0.0     0    3.7    True   0.0         1/0
COURT         122.34     -4   18    9    2    0   27.8     0.0     0    4.8   False   4.8         1/0
SUB-01          3.29     -3    8    5    2    0   23.1     0.0     0    0.0   False   2.8         1/0
Pumpwheel       7.83     -2   20   10    1    0   25.3     0.0     0    0.0    True   0.0         1/0
```

## Findings

- **Most big holders are busy bot wallets** (>100 transactions), so their funder cannot be
  traced cheaply; `linked%` is mostly 0. The bubble-map signal is weak with this method.
- **Dev history via the creator wallet is useless here:** every creator was 1 launch / 0
  graduations, i.e. devs use a fresh wallet per launch. A real dev check must follow the
  dev wallet's funder to earlier dev wallets.
- **`devsold`** appears on rugs and winners alike (step by step, PUMP, Pumpwheel won).
- **Best candidate: 5+ holders each ≥3% (excluding curve).** It flags bunk (15), QUIDD (8),
  TRIBUTE (6), MEMELIFE (5) — 4 losers, −103.6 USDT — and **no winner** (winners had 0–4).
  At ≥4 it also catches DOCAGENT and GAMBL but blocks PF (+31). n = 31 is far too small
  to trust either rule yet.
- Pump.fun's own panel flags top-10 > 20%; here almost every token (winners included) was
  above 20% at entry, so that alone would block nearly everything.

## What runs now

`InsiderShadow` logs an `insider_facts` line per assessed token (holders over 1/2/3/5%,
top-10 %, linked/fresh supply, clusters) on its own RPC client. It does not affect
buying. After a few days of runs the same table can be rebuilt from the log with a much
larger sample.
