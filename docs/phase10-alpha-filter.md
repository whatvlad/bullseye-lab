# Phase 10A Alpha Filter

Status: implemented for paper research. No signer or real transaction path exists.

The filter runs only after the active strategy emits an entry candidate. It does
not spend Birdeye CU on the global Pump stream.

## Global memecoin regime

Each candidate receives a point-in-time aggregate snapshot containing 15-minute
launches, trades, unique buyers, buy/sell quote flow, and 60-minute graduations.
The deterministic classifier labels the market `unknown`, `risk_off`, `selective`,
`risk_on`, or `mania`. Regime labels are shadow evidence and do not yet approve or
reject an entry.

## Deployer profile

The local point-in-time profile records observed launches, graduations, rejected
markets, graduation rate, early unique buyers, the largest early buyer share, and
the largest same-slot buyer group. Serial deployers with poor observed graduation
history are flagged in shadow mode.

## Birdeye holder cohorts

When the configured plan permits it, Bullseye calls the official Solana holder
profile endpoint for at most ten candidates per UTC day and caches a result for six
hours. The snapshot records current supply exposure for `dev`, `insider`,
`bundler`, `sniper`, `smart_trader`, and top-ten holders.

Extreme dev/insider/bundler/sniper exposure is a deterministic paper-entry block.
Missing or plan-forbidden Birdeye data remains unknown evidence in the journal and
does not manufacture a safe or unsafe value.

## Tradability gate

The constant-product simulator sizes the proposed order against fresh pool
reserves. An entry is rejected when modeled total price impact exceeds the active
strategy limit: 250 bps conservative, 350 bps balanced, or 500 bps aggressive.
This replaces an arbitrary fixed market-cap floor.

## Journal

Telegram's `Daily journal` view reports opened/closed positions, win rate, realized
PnL, average MFE/MAE, exit reasons, common entry rejections, and the latest Alpha
Filter candidate snapshots. Market/deployer observations remain explicitly marked
as shadow research until enough outcomes exist for calibration.
