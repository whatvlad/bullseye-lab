# Price model and provenance

Bounded prerequisite audit, 2026-10-01. No strategy thresholds changed; no experiment or live executor started. See [Cappuccinu evidence](CAPPUCCINU_PRICE_DISCREPANCY.md), [feed gaps](FEED_GAP_ANALYSIS.md), and [validation gate](PRICE_VALIDATION.md).

## Units and distinctions

`price_raw` is quote smallest units / token smallest units, not USD/token. SOL quote amounts are lamports; converting a token price into display units also requires token decimals. Native SOL is normalized to wrapped SOL at the execution boundary. A trade's average price, a post-trade marginal reserve mark, and a quantity-specific executable price have different meanings.

CoinGecko's SOL/USD or SOL/USDT conversion is a currency reference, **not** an executable token quote. No external executable buy/sell quotation or transaction simulation service is currently wired into this bot. All executable estimates here are conditional local simulations, not guaranteed fills.

## Source map and authority

| Value/subsystem | Exact origin and path | Appropriate authority |
|---|---|---|
| Discovery/event trade price | Native Pump/PumpSwap instruction/log decoders and PumpPortal normalization emit raw `TokenTrade.token_amount`, `quote_amount`, and optional reserves. Discovery alone supplies no fill price. Average execution price is `quote_amount / token_amount`. | Observed event amounts for that transaction only; native source slot/time where available. |
| Rolling observation price | `market_price.trade_mark`: virtual quote/token ratio first; otherwise `(real_quote + virtual_quote_offset)/real_token`; finally average trade if reserves absent. `intelligence/features/engine.py` stores this in `_TradePoint.marginal_price`, window open/close/returns, and latest price. VWAP uses observed transaction volume. | Stream marginal marks for momentum features, with average fallback explicitly identified. Neither is a fill guarantee. |
| Strategy decision price | `strategies/runner.py` copies the feature's `latest_price_raw` and price evidence into `StrategyDecisionCreated.decision_price`. Feature reference is immutable; lifecycle activity cannot refresh the price timestamp. | The exact observation used to make the strategy decision. Thresholds/scoring unchanged. |
| Pump curve/reserve price | Pump stream reserves; RPC bonding-curve decoder returns virtual/real token/quote reserves. Marginal mark is virtual quote/token. | Validated account reserves for execution estimates; stream reserve state for observational features. |
| RPC-derived price | `paper/market_refresh.py`: read market account, validate owner/mints/slot regression. Pump curve virtual ratio; PumpSwap decoded vault amounts plus pool virtual quote offset divided by base vault amount. Complete curves resolve a migrated pool where possible. | Refreshed validated reserves, labeled `rpc_primary_reserves` or `rpc_exit_reserves`; RPC response receipt time is not chain event time. |
| Executable buy quote | `paper/execution.py:simulate_buy`: requested portfolio amount / FX -> lamports; fee-inclusive integer Pump buy calculation; constant-product token output; real-token availability check. `executable_quote` = gross quote budget / pre-slippage token output, including the venue fee's effect on output. Impact is calculated separately from net curve input / output. | Quantity-specific curve/pool simulation at the recorded execution snapshot, conditional on fee/config assumptions. |
| Executable sell quote | `simulate_sell`: floor raw quantity; constant-product reserve output; real-quote availability check. `executable_quote` = pre-slippage gross quote / raw quantity. | Quantity-specific refreshed curve/pool estimate. Entry blocks do not disable this calculation. |
| Paper fill price | Execution delay is modeled; engine refreshes reserves after the delay. Buy adverse slippage reduces integer token output; sell adverse slippage reduces integer quote output. `simulated_fill` / `actual_fill_price_raw` = gross quote / filled token quantity. | Recorded conditional simulator output, never last-tick-as-fill. Version 2 fills are `ESTIMATED`, or `DEGRADED` for an explicit stale operator close. |
| Unrealized PnL mark | Position monitor simulates selling the **remaining quantity**. `execution_mark_json.net_portfolio_value` = gross portfolio proceeds minus venue/service/network/priority fees. Registry risk PnL and paper position cards use net value minus remaining basis. | Fresh executable net liquidation estimate with FX evidence. Missing/stale/quantity-mismatched mark blocks new exposure and displays unknown PnL. |
| Stop/exit-policy price | Automatic protective exits and peak tracking use quantity-specific gross simulated sell price, compared with actual gross entry fill price. Fresh state is checked again before executing. | Same raw price unit and execution-oriented model on each side. Fee/FX-inclusive net PnL is tracked separately; a 12% raw-price stop is not a promise of a 12% net loss. |
| Final realized PnL price | `storage/database/registry.py` books actual simulated quantity, gross proceeds, conversion and fees; reduces proportional remaining basis on partial exits. Buy gross includes venue fee; only service/network fees are added to buy cash cost. Sell cash deducts all fees. | Immutable fill ledger and cash reconciliation; market realism remains conditional. |
| Historical observed MFE/MAE | `storage/database/outcomes.py` observes stream `trade_mark` versus actual entry fill. Before this change, `registry.observe_open_position_price` also mixed RPC marks into these excursions. | Observational labels only. New execution marks no longer overwrite observational excursions. Old rows are not backfilled or relabeled as verified execution evidence. |
| Tracked-wallet valuation | `storage/database/wallets.py` tracks observed wallet buys/sells and last observed mark; estimated unrealized value is remaining quantity times that mark minus basis. | Observational wallet analytics, not executable liquidation or authoritative paper portfolio PnL. |
| Enrichment/display references | Birdeye enrichment, DexScreener pool lookup, Pulse summaries and CoinGecko conversion are auxiliary references. SOL/USDT = SOL/USD divided by tether/USD; provider `last_updated_at` controls freshness. | Explicitly sourced enrichment/FX only; never replace executable reserves silently. |

## Comparisons audited

1. Existing position peaks, stops and risk/card unrealized PnL mixed observational marginal marks with impacted entry fills. Stream mutation of position exit marks is removed. Quantity-specific execution marks drive exit policy; net execution value drives risk/card PnL.
2. Legacy `expected_fill_price_raw` was a marginal observation despite its name. Version 2 makes it the pre-slippage quantity-specific curve quote; `reference_price` retains the marginal reserve ratio. Legacy fills remain version 1/unknown provenance when parsed.
3. Observed MFE/MAE versus final fee-inclusive ledger PnL cannot establish achievable profit capture. They are now explicitly distinct.
4. RPC-versus-stream percentage uses only a same-market reserve reference; average transaction price is not eligible. Migration clears the comparison. Unknown comparison is null, not zero. The percentage can reflect elapsed market change as well as provider disagreement; its timestamps must be assessed together.
5. Signal drift compares two execution-reserve marginal references; strategy `decision_price` is retained separately. Drift is an entry safety check, not realized PnL.
6. Wallet marks and stream-only historical runner labels remain observational and must not enter execution/PnL claims.

## Required metadata and order evidence

Execution snapshots, fills and persisted order-domain evidence expose `price_source`, `source_timestamp`, `received_timestamp`, `price_age_ms`, `feed_age_ms`, `price_source_disagreement_pct`, and `data_quality`. Rolling snapshots and strategy decisions carry observation evidence. Native normalized events retain provider, source time, receipt, slot, raw transaction amounts and reserves.

For RPC, `source_timestamp` and `price_age_ms` are null because account slot does not provide a wall-clock event timestamp. Separate `received_age_ms` measures response receipt age; `data_quality` explicitly says source time unknown. `source_slot` remains available. A responsive RPC must not silently mean known chain-price age. For streams, age is from the reported source time; PumpPortal's receipt-derived source time is explicitly estimated (`feed_timestamp_estimated`), including historical events that incorrectly left the old flag false. Entry policy rejects estimated source times by default. RPC refresh never replaces `feed_timestamp` with now.

Every engine/manual order has price evidence with `decision_price`, `reference_price`, `executable_quote`, `simulated_fill`, `price_impact`, `slippage`, and `fees`. Unavailable values on rejected orders are null. For fills: prices are raw quote/token, impact/slippage are basis points, fees are portfolio currency. Component fees and reserve snapshots remain recorded. Gross sell price excludes fee deductions; net value subtracts them exactly once.

## Availability and exit recovery

| Failure | New exposure | Existing exposure |
|---|---|---|
| No primary stream / WebSocket disconnect | Feed clock ages; block stale or unknown critical observations. | Independent timer attempts dedicated exit RPC, then primary RPC; no trade callback required. Missing stream context is reconstructed from the open position's market address for RPC recovery. |
| RPC unavailable/degraded | Require healthy refreshed RPC by default. | Try alternate RPC; fresh complete stream reserves can still support a conditional exit estimate. |
| Severe source disagreement | Block against explicitly configured disagreement limit; missing limit or comparable reference also blocks. | Surface discrepancy and continue an executable recovery attempt. It is never interpreted as stable price or allowed to disable an emergency exit. |
| Quote/currency provider unavailable | Reject incomplete/unavailable quote evidence. | Persist failed attempt, keep exposure open, retry on subsequent monitor cycles. No fictitious currency conversion or fill. |
| All market state stale/incomplete | Reject entry. | Persist recovery rejection; do not manufacture an exit. Next monitor/stream event retries; provider circuits rate-limit failures. |

Open-position events are prioritized in the paper queue. Entry retries no longer hold the exit monitor lock. The dedicated exit RPC is tried first for exits and is not used by entry refreshes. Each timer attempt has a configurable timeout; one exception cannot stop recovery for the other positions. The existing monitor interval and provider circuit cooldowns bound attempts. This preserves a recovery path, not a guarantee of liquidity or continuous exit availability. A slow unrelated provider/model still has finite scheduling impact.

Operational entry controls are separate from strategy thresholds: `paper_entry_max_feed_age_seconds` (default matches existing 5-second market freshness policy), `paper_entry_require_rpc=true`, `paper_entry_allow_estimated_feed_time=false`, and `paper_entry_max_source_disagreement_percent` (no inferred default; unconfigured blocks entry). Market/FX freshness, monitor interval and exit-attempt timeout remain explicit settings. Test disagreement values are fixtures, not recommended trading calibration.

## Remaining model limits

Pump fee/creator configuration, PumpSwap executable fee calibration, external transaction simulation, and chain freshness of an RPC response beyond slot regression are not fully verified. Cached/lagged RPC state can have a recent receipt. PumpPortal has no comparable chain slot/event timestamp. Complete-pool recovery and multiple account reads can span slots. Do not claim exact on-chain fidelity or causality from these records. Prospective validation stays blocked pending actual operational source/freshness evidence and frozen safety configuration.


## Current trading universe: standard Pump.fun only

The standard-only prerequisite supersedes ecosystem-wide readiness conclusions.
See [STANDARD_PUMP_FUN_RUNNER.md](STANDARD_PUMP_FUN_RUNNER.md). Mayhem, PumpSwap, migrated,
ambiguous, unknown-state and unverified execution markets cannot authorize entries.
The simulator's fixed Pump 95/30 bps fee components are explicitly ESTIMATED until
bound to synchronized canonical config/state evidence; they are not unconditional
on-chain fee authority. Existing exposure retains generic exit recovery.
Runner thresholds and disagreement bands remain unchanged, and the experiment is BLOCKED.
