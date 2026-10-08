# Mutation coverage

The production tracker is deliberately incomplete. A trade-only feed cannot prove
absence of direct SPL vault transfers or silent account/config changes. Native
instruction/data inspection follows the invocation stack: unrelated token-program
TransferChecked logs are not confused with native program instructions. Unknown
native instructions/events, decoder failures and truncated logs invalidate cached
continuity and queue a coalesced reconciliation request. Where the affected market
cannot be identified, invalidation conservatively applies to all cached markets.

| Venue/mutation | Handling | Remaining limitation |
|---|---|---|
| Pump.fun ordinary buy/sell | Explicit POST and exact integer real/virtual transition checks | Log-only coverage incomplete |
| Pump.fun multi-event | UNKNOWN; no guessed intermediate state | Requires transaction-specific proof |
| Pump.fun create | Discovery/curve mapping | Full identity/config bootstrap incomplete |
| Pump.fun complete/migrate | Lifecycle update and invalidation | Rebootstrap new market; no trusted migration reserve inference |
| Pump.fun virtual/Mayhem/quote/config/creator changes | Unsupported native instruction/event invalidates | Mutation arithmetic not implemented |
| PumpSwap buy/sell | Actual transfer PRE→POST; exact next-PRE checks | Trade-only coverage incomplete |
| PumpSwap create_pool | Discovery and account validation | Initialization reserve reconstruction unsupported |
| PumpSwap deposit/withdraw | Unsupported native instruction/event invalidates | Exact LP and vault mutation decoder unsupported |
| PumpSwap boost, creator, fees/config, migration changes | Invalidate/rebootstrap | Exact non-swap state transition unsupported |
| Direct curve/pool/vault changes | Explicit invalidate API; detected mismatches on next trade/RPC | No production account subscription or exhaustive mutation feed |
| WebSocket outage/truncated logs/decoder failure | Invalidate cached history | Does not identify the missing transaction |
| RPC owner/mint/vault/slot decode failure | Reject and invalidate | Retry/recovery required |

The full primary instruction inventory, including writable account names, is in
`analysis/production_state_replay.json.primary_idl_inventory`. Both current official
IDLs were fetched in two documentation requests, separately from RPC billing.
Sources: [Pump IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json)
and [PumpSwap IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_amm.json).
Their content hashes are retained; the runtime decoder remains pinned to the
previously verified compatible revision.

Pump.fun inventory includes set_params, set_virtual_quote_reserves,
set_mayhem_virtual_params, migrate/migrate_v2, quote-control and fee/buyback/holder
config instructions. PumpSwap inventory includes deposit, withdraw, create_pool,
boost_buy_and_burn, init_boost/toggle_boost, update_fee_config, creator/config/admin
changes and fee transfers. All native instructions outside the narrow implemented
ordinary-swap whitelist fail closed, including variants not yet admitted to that
whitelist and ancillary user-volume instructions. This causes conservative
UNKNOWN classifications; it is not evidence that all such instructions moved reserves.

Unsupported mutations do not regain execution readiness from a later plausible
price. RPC reconciliation validates accounts first. Open-position and exit refreshes
continue even when observational state is UNKNOWN, INCOMPLETE or DIVERGED.
