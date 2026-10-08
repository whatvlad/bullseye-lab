# Market data calibration — BLOCKED

Passive pilot 2026-10-01T18:50:42.139172+00:00 to 2026-10-01T18:51:22.997621+00:00 (40.858s).
Stopped at its hard 200-RPC-request cap before the 180s wall-clock cap. No orders, worker,
experiment activation or database writes. Strategy settings and live mode unchanged.
180 actual prospective pairs, 8 tokens;
720 quote-size rows, not 720 independent pairs. Targets: 1000 pairs / 100 tokens.

| Venue | Tokens | N pairs | Median % | p75 % | p90 % | p95 % | p99 % | Max % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pump_fun | 7 | 171 | 2.3775 | 8.5747 | 16.0007 | 28.0181 | 57.0775 | 63.6585 |
| pump_swap | 1 | 9 | 1.3016 | 1.3904 | 115.4467 | 343.0169 | 525.073 | 570.587 |

All-pair absolute disagreement: median 1.6161%, p95 32.6203%,
p99 59.8836%, max 570.5870%. These are pilot observations, not NORMAL bands.
Same-slot comparisons: `{"N": 27, "median": 1.4266494325383294, "p75": 7.291033137026499, "p90": 25.27534315687347, "p95": 41.000146691268775, "p99": 54.73246483263765, "max": 58.880137946298376}`. Even same-slot comparisons
can represent different transactions, event pre/post state or end-of-slot account state.
No historical Cappuccinu ticks or fixture data were included.

The independent collector imports no trading engine, order publisher or database.
It subscribes to confirmed native logs for both programs and free PumpPortal creations/migrations.
Unknown markets cause no RPC reads. SOL markets created during the run enter a local filter
after two positive-amount trades. Queued observations older than two receipt seconds are rejected
as pairing failures; this is a research synchronization filter, not a strategy threshold.
Mayhem and non-SOL markets are excluded. Fee fidelity for cashback/rewards is not established.
Pump.fun ages are below 60s; PumpSwap token age is UNKNOWN. Pool creation age is recorded
separately and cannot substitute for token creation age. Original capture lacks the mint-set
intersection needed to prove an exact launch-only conversion. The collector now retains those
sets for future captures and caps each market at ten attempts with a one-second pairing interval.
Selection is biased toward young, active tokens; repeated snapshots of eight tokens are correlated.
Native activity received 251 tracked-market trades;
the collector received many more logs for unknown markets without querying their accounts.

Quote sizes .01/.025/.05/.1 SOL are research notionals only. Buy uses gross SOL budget;
sell uses token quantity of equal marginal SOL notional, not round-trip buy inventory.
Venue fees are modeled, service/network costs excluded and labeled. Slippage is UNKNOWN;
zero bps is a calculation scenario. Gross executable sell price is separated from net fee-adjusted
proceeds. All quotes remain ESTIMATED. JSON preserves integer reserves and complete local quote
evidence; CSV stores four rows per pair with explicit sample_id. The original capture is retained
in market_data_raw.json. Offline quote replay corrected inherited RPC provenance labels without
changing captured reserves, slots or times. The original collector hash stays in run metadata.

Distributions contain N/median/p75/p90/p95/p99/max separately for venue, quote size,
liquidity, age, adjacent-tick volatility and observed activity. Liquidity buckets use effective
quote reserves including virtual liquidity, not withdrawable depth. Unobserved buckets provide
no support. No NORMAL/ELEVATED/SEVERE values can be frozen from this sample.

Source policy: discovery can use free PumpPortal plus native creations; momentum needs native
trade events with gap/slot checks, with PumpPortal trade use still unvalidated. Entry and exit
execution require current owner/mint-validated reserves and quantity-specific executable quotes.
Exit recovery uses the existing independent RPC path. Unrealized PnL uses net executable full-size
sell proceeds less remaining basis. Marginal trades and reserve marks are references, not fills.

Both streams and both RPCs worked during this short pilot. That does not establish reliability
under outages. Large disagreement, missing venue/cohort coverage, fee fidelity and unpriced CU
usage keep the experiment BLOCKED. The experiment start gate now requires calibration PASSED
in addition to the earlier price prerequisite gate; this run cannot activate it.

Reproduce with `python -m memebot.research.market_calibration --seconds 180 --max-rpc-requests 200`.
Running again replaces primary outputs; archive them first. No extra provider spending is needed
to inspect the existing evidence. Before a larger capture, set a reviewed provider CU budget and
improve fair sampling so a handful of active tokens cannot consume the whole budget.
