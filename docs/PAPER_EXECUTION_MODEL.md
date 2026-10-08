# Current-state standard Pump.fun PAPER execution

PAPER model version 3 uses a current atomic account bank, not an observed trade as a guaranteed fill. Live execution remains unavailable in `Settings.execution_mode`.

## Authorization and provenance

Cheap discovery screens standard Pump.fun, explicitly non-Mayhem markets. PumpSwap, completion/migration, unresolved router/multi-event routes and explicit malformed or incompatible state are excluded before deep risk collection. Ordinary historical closure and index lag are diagnostics. A scheduled risk assessment first verifies current canonical identity; its existing identity guard remains in place.

`CurrentPaperMarketRefresher` reuses the canonical account decoder in `CandidateProofService._bundle` with no historical proof object. One `getMultipleAccounts` bank includes the mint, curve PDA, legacy and Token-2022 vault alternatives, Pump global configuration, fee configuration, and creator-sharing binding. It verifies owners, canonical addresses, token account authority/state, supported mint extensions, quote asset, current mode, completion, and simple fee route. Unsupported sharing, cashback and holder-reward branches fail closed. Positive virtual reserves and nonnegative real reserves are mandatory.

The atomic bank slot and local receipt time identify the simulated execution state. The source timestamp is unknown rather than invented from receipt time. A read taking over five seconds is rejected; the existing configured market freshness limit applies again at fill. Stream age and source disagreement remain separately recorded diagnostics. An already configured disagreement limit still applies; this task configures no new band.

The engine retains its preliminary current-state refresh and its mandatory final atomic refresh after simulated execution delay. Neither authorizes a fill without canonical identity/configuration verification. Full history reconstruction, four fences and `COMPLETE_FOR_WINDOW` do not authorize or veto an otherwise compatible current bank in PAPER.

## Exact quote and pessimistic fill

`standard_math.buy_exact_input` and `sell_quote` use raw integer reserves and the selected on-chain protocol/creator fee tier. Buy input is floored to lamports; exact protocol and creator rounding is preserved. Buy token output is reduced by configured friction and floored. Sell gross output is reduced and floored; protocol/creator fees are conservatively retained from the unadjusted exact sell quote. Real-reserve capacity remains enforced.

Default extra slippage, latency penalty and adverse adjustment are each 50 bps, totaling 150 bps. The existing provider estimate is 50 bps of unadjusted gross quote. Network and priority estimates are separately recorded as 0.00001 and 0.0001 SOL. Configured values in `analysis/paper_execution_assumptions.json` take precedence over these defaults. Protocol/creator fees are verified on-chain; external costs and execution friction are explicit assumptions, not observations.

Buy gross quote already includes venue fees. Portfolio cash cost adds only provider and network/priority costs, avoiding double counting. Sell proceeds subtract all venue, provider and network/priority costs. SOL conversion uses the separately timestamped quote-price provider. This produces portfolio-currency results, which include SOL conversion effects.

Every fill retains decision/reference/executable/fill prices, exact curve/config binding and slot, token and SOL amounts, impact, combined slippage, separate friction components, fee evidence and timestamps. Rejected orders retain price evidence in their domain event even when no fill exists.

## Exits and marks

Exits use fresh atomic state and the same exact sell model. The dedicated exit RPC is attempted before the primary fallback. Failure cannot create a synthetic realized exit. Open positions and recovery failures remain durable for retry.

Unrealized value is estimated executable net liquidation value. Stored marks are valid only within the configured freshness limit; missing/expired execution marks make unrealized PnL unavailable. Raw stream MFE/MAE remains observational. Separate executable MFE/MAE tracks net liquidation return against the remaining cost basis, with its own peak timestamp. Partial exits change that basis, so this statistic is explicitly not an unchanging full-position return.

## Performance attribution

Completed-trade net PnL is measured from actual simulated fills. Gross PnL before fees adds those trades' fees back; it still includes friction. A separate price-only counterfactual undoes configured entry quantity and exit gross reductions using each actual exit bank. Strategy price PnL minus counterfactual friction minus fees reconciles to net PnL subject to integer rounding. When the counterfactual quote is unavailable, attribution is null. This is model attribution, not causal market evidence.

Drawdown uses closed-trade realized equity. It does not imply that unmarked open exposure has zero drawdown. Undefined win rate, expectancy, profit factor, holding statistics and setup rankings remain null when the sample cannot support them. Earlier historical trades are not retroactively certified by this model.
