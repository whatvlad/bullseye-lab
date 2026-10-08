# Standard Pump.fun PAPER cost model

The intended execution assumption is PumpPortal Local. Its official fee is **0.5% on each trade**
before slippage, with network and Pump fees separate. Native market discovery does not imply
a direct execution route. No direct SDK signer route is selected, and PAPER actually sends no trades.
Fee retained. Sources: [PumpPortal fees](https://pumpportal.fun/fees/) and
[Local Transaction API](https://pumpportal.fun/local-trading-api/trading-api/).

| Component | Classification | Basis / assumption |
| --- | --- | --- |
| protocol_fee | MEASURED_OR_ONCHAIN | per-fill canonical atomic global/fee config and dynamic tier, integer rounding |
| creator_fee | MEASURED_OR_ONCHAIN | per-fill canonical atomic creator/config rate; no unsupported route estimates |
| lp_fee_standard_curve | NOT_APPLICABLE | {"bps": 0} |
| price_impact | MEASURED_OR_ONCHAIN | quantity-specific curve output derived from verified reserves; not an observed real-world fill or own-paper-trade state overlay |
| modeled_provider_fee | ROUTE_APPLICABLE_ESTIMATE | {"bps_per_side": "50"} |
| network_priority_fee | ROUTE_APPLICABLE_ESTIMATE | {"network_sol": "0.00001", "priority_sol": "0.0001"} |
| simulated_latency_penalty | CONSERVATIVE_SIMULATION | {"bps_per_side": "50", "compute_ms": 50, "submission_ms": 750} |
| additional_slippage | CONSERVATIVE_SIMULATION | {"bps_per_side": "50"} |
| adverse_fill | CONSERVATIVE_SIMULATION | {"bps_per_side": "50"} |

Standard buys use fee-inclusive exact input: protocol/creator fees are embedded in gross entry
cash input, so the registry adds only modeled provider and network costs on top. Sells subtract
venue/provider/network costs from simulated gross proceeds. No double fee deduction was found.

Curve quotes derive quantity-specific impact from saved canonical reserves. The independent
paper bank does not incorporate the hypothetical bot's own previous buy/sell reserve change.
The same-bank entry round-trip probe is therefore a conservative entry diagnostic, not a
measured actual round-trip or proof that costs will take exactly that percentage.

The previous saved-bank hurdle ranges are 8.50–8.96% (12-trade portfolio) and 7.79–8.92%
(8-trade reset portfolio). Costs and the cost-gate formula remain unchanged. New sample hurdle
distribution is recorded only for actual corrected entries, otherwise N/A.

Each side still has 50bps latency penalty + 50bps additional slippage + 50bps adverse fill.
The configured 50ms computation + 750ms submission wait remains; prices refresh after waiting.
These penalties are conservative assumptions, not empirically calibrated market losses.

The simulator does not measure real dispatch, priority-fee auctions, rent/account creation or
transaction inclusion. These remain limitations of economic PAPER-to-LIVE comparison.
LIVE remains disabled. No costs were removed to improve historical profitability.

Machine-readable assumptions and classifications: `analysis/paper_cost_model.json`.
