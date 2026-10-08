# Phase 9A: research-derived paper edge

Status: implemented as a testable hypothesis; not validated for live capital.

## Hypothesis

Bullseye now tests whether fast real-SOL accumulation at comparable Pump bonding
curve progress, achieved by distributed buyers rather than one dominant wallet,
has more predictive value than raw price momentum. The empirical motivation is
the 2026 Pump.fun study of 655,770 launches, where graduation was rare and reserve
accumulation velocity plus fewer swaps to the same curve state were among the
strongest predictors. The same study also found frequent dump events and weak
naive trader profitability, so the implementation includes a separate dump
hazard exit and makes no profitability claim.

Primary research:

- <https://arxiv.org/pdf/2602.14860>
- <https://arxiv.org/abs/2607.02795>
- <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4481308>
- <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6858778>

## Point-in-time features

Every rolling feature snapshot can now record:

- real quote-reserve change and velocity;
- buyer quote-volume HHI and largest-buyer share;
- the percentage of buy volume whose wallet was actually attributable;
- the latest trade-to-trade price return;
- robust latest-sell size using a median/MAD score.

Only trades at or before the feature watermark are used. Version 1 deliberately
uses rolling windows, not a fabricated launch history after a process restart.
Full persisted launch-level landmarks and out-of-sample calibration remain a
later Phase 9 slice.

## Execution costs

Pump bonding-curve paper fills use 125 bps. Canonical PumpSwap paper fills select
the official 125-to-30 bps tier from decision-time SOL market cap; other venues
retain the configured fallback. The tier calculation assumes the standard Pump
fixed supply of one billion tokens.

Official references:

- <https://pump.fun/docs/fees>
- <https://pump.fun/docs/bonding-curve>

The smart contract remains authoritative and Pump may change fees. Historical
paper results must therefore retain the effective fee evidence stored on each
fill.

## Validation rule

Do not promote this component or any strategy using it toward live execution
based on a profitable night.
Evaluate chronological, fee-adjusted cohorts with untouched holdout periods,
report the number of tested variants, and use a multiple-testing correction such
as the Deflated Sharpe Ratio: <https://doi.org/10.2139/ssrn.2460551>.

## Portfolio risk governor

Phase 9A applies strategy-independent entry gates before every automatic or
manual paper buy:

- 1% base and 2% maximum position sizing;
- five simultaneous positions and 25% maximum cost-basis exposure;
- a 5% UTC-day loss limit including current mark-to-market P&L;
- a 30-minute entry cooldown after three consecutive losses;
- a 60-minute re-entry cooldown for the same mint;
- a database-enforced single open position per portfolio and mint.

Take profit now begins at 25%, trailing protection activates at 12% with an 8%
drawdown, and the migration pauses new entries. These controls bound future paper
risk but cannot undo gaps that occurred before the next observable reserve state.

The paper engine now also refreshes every open position from pool account state on
a short timer. Stop-loss, take-profit, trailing-stop, and maximum-holding exits no
longer require another trade notification for that mint. A separate low-volume
exit RPC can remain available if the discovery provider is halted.

## RPC credit governor

Stream-derived activity is used as a free prefilter before the expensive on-chain
holder and mint assessment. Assessments have configurable hourly/daily budgets and
a longer reassessment interval. Repeated WebSocket `InvalidStatus` responses open a
circuit breaker: reconnect probes slow to 15 minutes, duplicate health events are
suppressed, and new paper entries are paused until an operator explicitly resumes.

Trade outcomes are reconciled against the authoritative position projection.
This repairs historical rows that remained marked open after repeated entry/exit
cycles in the same mint.
