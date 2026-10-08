# Corrected operational PAPER baseline

This patch fixes the existing bot's signal, exit and attribution defects. LIVE remains disabled;
`runner-edge-prospective-v1` remains BLOCKED. No new proof gates, providers, strategy families,
wallet/social intelligence or LLM signals were added. Ollama remains off. Source fingerprint:
`3e149b51a918e6ebee98d6fdeed1603660307a2ade0f50876339c177518ff7ba`.

## Historical entry signal

`strategies/price_signal.py` checks a positive decision/reference price, the configured rolling
price-change feature, observationally healthy provenance, POST_TRADE semantics, supported
continuity and reported source time. The window must have at least two usable price samples,
positive endpoints, no missing-price event and price span at least the preset's existing
minimum observation duration. For aggressive v10 this is **3 seconds of price observations
inside the 10-second scoring window**, not a claim of complete ten-second transaction coverage.
Coverage is measured explicitly by `price_sample_count`, `missing_price_sample_count` and
`price_observation_span_seconds`. Unknown transaction/stream continuity still invalidates prices;
no retrospective RPC bank is relabeled as historical momentum.

The rolling engine invalidates price-change/velocity when an event in the window has no usable
price. A later valid endpoint cannot average that missing event away. Missing mandatory
momentum subinputs produce `component_status=INCOMPLETE`, `missing_required_inputs`, and reduced
`overall_signal_completeness` (weighted component completeness, not a probability of profitability).
Unavailable optional components remain visible. An absent price change produces
`UNKNOWN_REQUIRED_PRICE_CHANGE` and cannot bypass the extension guard. The PAPER engine independently
rejects null/legacy/incomplete historical decisions before execution RPC.

## Unchanged selection and risk controls

Active strategy: `aggressive`, version 10. Entry SCORE
55; watch SCORE 45. Existing trade/buyer,
flow, concentration, extension, regime, canonical identity and execution-state guards remain.
Position allocation, adaptive sizing, fee assumptions, RPC budgets and daily breaker parameters
match the saved pre-fix configuration. Stop remains 12.0000%, TP
100.0000%, primary trailing configuration remains unchanged.

**The stop's metric changes:** it now uses quantity-specific net executable liquidation divided
by actual remaining portfolio-currency entry cost basis. Gross raw-price movement remains a
diagnostic. TP/trailing policy is unchanged. Exit refresh, quote validation and the existing
pessimistic simulation remain mandatory.

## Exit priority and evidence

Native receipt wakes for watched open markets bypass the ordered discovery/analysis queue.
They carry identity/slot only; they do not authorize a price or fill. Each mint has its own lock,
and position identity is re-read inside the lock. Relevant slot and last retained bank slot
bound the final atomic refresh. The watchdog dispatches per-market tasks, so a slow RPC for
one market does not postpone the next watchdog for another. Existing independent exit RPC
and fallback RPC remain in use. Recovered/stale banks never become fabricated liquidation.

Each exit has receipt/ingestion, evaluation, RPC, trigger and fill timestamps plus queue/lock/RPC
and simulated-delay durations. Detection and final banks are retained. A price recovery is
re-evaluated before fill; further movement is recorded in trigger-to-fill price change.

`execution_mark_json.exit_evidence` durably holds a maximum 2048 marks, total/dropped counts,
quantity and remaining cost basis, gross quote/net liquidation, gross/net PnL, segmented net
peak and drawdown. Gross PnL in the path is the raw-SOL price-change component converted at the
mark's SOL/portfolio FX; **net PnL uses actual portfolio-currency cost basis including entry costs
and FX**. Portfolio performance is separately reconciled from actual PAPER cash flows.
Partial closes start a new remaining-basis peak segment. Shadow policies retain whole-entry
realized-plus-liquidation MFE/MAE independently of that segment.

Three shadow policies use the same entry and executable marks, with no additional orders:
CURRENT_POLICY, EARLIER_PROFIT_PROTECTION and DEFENSIVE_PROFIT_PROTECTION. Earlier uses TP/2 and
activation/2 with the current fixed width; defensive uses TP/4, activation/4 and width/2.
CURRENT follows existing dynamic runner width/hold behavior. These predeclared diagnostic
ratios are not optimized or selected. Mark-time shadow exits omit subsequent submission delay
and are optimistic timing counterfactuals; shadows still open at the primary close are censored.
Mark-only shadows do not reproduce event-only dump-hazard signals.

## Portfolio attribution and deployment

Telegram portfolio reset is transactional, refuses any open exposure, pauses entries and
creates a linked experiment cohort for the new active portfolio. If the previous experiment
is stopped, initialized strategy/control still create a new cohort. Previous portfolios and
results remain. Reports expose both their portfolio ID and the currently active portfolio ID.
The eight historically orphaned reset trades were attached to a stopped legacy cohort; its
copied settings are explicitly UNVERIFIED, not relabeled as corrected data.

Helius WSS returned HTTP 429. A one-subscription probe on the **already configured Alchemy RPC**
succeeded; the existing native adapter now uses that acknowledged WSS endpoint. No provider
architecture or higher-tier purchase was introduced. This endpoint difference is a comparison
confound. Alchemy subscriptions use bandwidth billing: see
[official subscription documentation](https://www.alchemy.com/docs/reference/solana-subscription-api-endpoints).

Regression gate passed: **508 tests**, Ruff, and mypy over 141 source files. New cases cover null
inputs, missing window/subinput/provenance, the extension guard, gaps between good ticks, net
stop logic and remaining basis, independent market progress, duplicate-exit exclusion,
receipt wakes, a nonblocking watchdog, bounded durable shadows and reset/cohort association.

See `PAPER_CORRECTED_RUN.md` for actual prospective results. Passing tests does not establish edge.
