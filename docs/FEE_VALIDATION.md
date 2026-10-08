# Fee validation — ESTIMATED

Local Pump.fun uses 125 bps, with buy fee components 95 protocol + 30 creator bps.
Local canonical SOL PumpSwap uses market-cap tiers 125 down to 30 bps and a fixed 1B-token
supply assumption. The [current official fee page](https://pump.fun/docs/fees) supports the
published bonding-curve total and canonical tier schedule, but differentiates noncanonical
pools (30 bps), creator behavior and other modes. This is documentation agreement, not
per-market on-chain proof.

One chain read of PumpSwap GlobalConfig at slot 452373083,
owner validated, captured fallback LP/protocol/creator bps:
20/5/5.
These are fallback fields, not evidence that the sampled canonical markets charge their sum.
Raw account bytes and SHA256 are retained in provider_costs.json.

The [official fee-program logic](https://github.com/pump-fun/pump-public-docs/blob/main/docs/FEE_PROGRAM_README.md)
requires FeeConfig when available, actual mint supply, market-cap tier selection and canonical
pool-authority verification. These were not obtained for every sampled market. Current/pinned
official IDL layout comparison is retained in fee_idl_validation.json with hashes. Added reward,
buyback or configurable creator fields require explicit support before exact-fidelity claims.
Pool/event prefix compatibility does not prove complete fee handling.

Creator existence, cashback/rewards, custom configurations and total protocol/creator/LP costs
are not automatically interchangeable. Pump graduation is an additional documented 0.015 SOL
operation, not a recurring fee for every research quote. Network signature/priority fees,
account creation/rent and transfer-fee extensions are route-dependent and unverified here.
No transaction was submitted or simulated against the chain. Local reserve quotes therefore
remain ESTIMATED and cannot support an exact or safely bounded fee gate.

PumpPortal [official fees](https://pumpportal.fun/fees/) currently separate Local transaction
service fee 50 bps from Lightning 100 bps, before slippage and excluding network/venue fees.
Research quotes use neither service and explicitly exclude those charges. Production routing
must match its actual fee model. Zero slippage in this calibration is a scenario, not a forecast.
