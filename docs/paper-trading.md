# Realistic paper trading

Status: Phase 5 implemented  
Safety boundary: simulation only; no signer, private key, transaction, or swap API

## Entry flow

Only `enter_candidate` from the currently active strategy reaches the paper
engine. Before simulating a buy it verifies:

- an active paper portfolio exists;
- the same token is not already open;
- the open-position limit is not reached;
- the latest trade/reserve state is fresh and not after the decision;
- the quote asset is wrapped SOL;
- a timestamped SOL price is available and fresh;
- cash covers the notional plus simulated network/priority fee.

Any failed condition creates a persisted rejected paper order with a reason. It
never creates a fallback price.

If an otherwise valid automatic entry reaches execution with a market snapshot
older than the five-second default, it becomes a persistent pending entry for 30
seconds instead of being discarded. The next fresh token trade repeats the
execution gates before a fill. The pending action survives worker restarts and
cannot create a duplicate position.

## Quote accounting

The official CoinGecko keyless public `/simple/price` endpoint supplies SOL/USD
and USDT/USD together. USD portfolios use SOL/USD directly. USDT portfolios use
`SOL/USD ÷ USDT/USD`, preserving the distinction between USD and USDT. Responses
are cached for 20 seconds and carry provider/update timestamps.

Token and SOL quantities remain raw on-chain units in fills. Cash, cost basis,
fees, and PnL use `Decimal` in the selected portfolio currency.

## Fill model

The simulator uses the latest Pump virtual reserves or PumpSwap real base plus
effective quote reserves. A constant-product calculation models order-size price
impact. Configured venue fee, network fee, priority fee, latency slippage, compute
delay, and submission delay are recorded on every fill.

Fee defaults are conservative experimental assumptions, not claims about current
venue fees. Because dynamic fee schedules and the exact future block state are not
fully known, current fills are labeled `high_confidence`, not
`exact_onchain_model`.

The recorded timeline contains signal, paper decision, simulated submission,
simulated fill, market observation, and quote-price observation timestamps.

## Sizing and exits

The active preset starts at 5% of initial capital and scales toward 10% as its
score rises from the entry threshold toward 100, capped by available cash. The
defaults also enforce ten open positions.

Positions support:

- 20% stop loss;
- 50% partial take profit selling half the position;
- trailing activation after +25% and a 15% trailing stop;
- 30-minute maximum holding time.

Manual full closes use a separate path. The recommended action waits up to 30
seconds for the next fresh token trade and then closes from current reserves. An
explicit operator force-close may use the last known reserves when no fresh trade
arrives. Forced stale fills are marked `degraded`, retain the snapshot age in
execution evidence, and display a P&L warning. Both paths remain simulations.

```dotenv
BULLSEYE_PAPER_PENDING_ENTRY_TTL_SECONDS=30
BULLSEYE_PAPER_PENDING_CLOSE_TTL_SECONDS=30
```

All values are environment-configurable research hypotheses. Exits use a current
trade/reserve snapshot and the same fee/latency fill model as entries.

## Accounting invariant

After each fill:

```text
cash + remaining open cost basis = initial cash + realized PnL
```

Buy cost basis includes gross notional plus network/priority fee. Sell proceeds
subtract venue, network, and priority fees. Partial exits allocate cost basis in
proportion to quantity sold. Tests enforce reconciliation.

## Commands

```powershell
bullseye portfolio
bullseye paper-orders --limit 20
bullseye portfolio-create --name "Experiment" --capital 1000 --currency USDT
```

Creating a portfolio deactivates the previous one without deleting its history.
Phase 6 exposes the same lifecycle through the allowlisted Telegram panel.
