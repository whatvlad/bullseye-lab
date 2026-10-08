# Market identity and reconciliation

A mint does not identify an executable market. `MarketIdentity` caches venue,
program, market address, base/quote mints, orientation, base/quote vault addresses,
curve address, migration flag, virtual offsets, config version and a separate
canonical-verification flag. Cache keys are market addresses. Unbootstrapped
mint-keyed research observations are explicitly prefixed `unbootstrapped:` and
cannot authorize execution.

## Verified checks and unresolved bootstrap

PumpSwap refresh checks program owner, pool discriminator/decode, pool base/quote
mints and orientation, SPL program owners, vault mints and vault authority equal
to the pool. Both vault balances must share a slot and cannot precede the pool
read. State cannot regress behind the current tracked slot. Vault/pool identity
or virtual-offset change invalidates the cache and requires rebootstrap.

Pump.fun refresh validates program owner, discriminator/reserve decode, quote asset,
completion/migration and slot monotonicity. The canonical curve-to-mint address
derivation and independent curve vault/mint binding are not newly implemented.
Thus the cached base mint is context, not a newly proven on-account mint field.

Canonical PDA derivation, creator/migration authority, config account version,
dynamic fee configuration and complete direct-account coverage remain unverified.
`canonical_verified=False`, `config_version=None`; these are never filled with
assumed constants. Even a successful reserve RPC read remains INCOMPLETE for local
execution readiness. The existing fee model is an explicit simulation assumption,
not an exact fee-config bootstrap. Entry blocks remain active.

Config/identity mismatch, unexpected owner/mint, pool change, graduation/migration,
unknown native mutation, disconnect and decode failure invalidate local trust.
Unsupported or silent config changes are covered conservatively by incomplete
coverage and mandatory execution RPC, not by a claim of exhaustive detection.

## Policy hooks

`ReconciliationPolicy` supports bootstrap, configurable periodic/event-count,
divergence, pre-entry, open-position and exit duties. Periodic and event-count
defaults are unset. Requests are coalesced per market and bounded by tracker
capacity; `pending_reconciliation_markets(eligible, limit=...)` admits only selected
exposure/candidates within a caller's read budget. No broad discovery repair drain
is enabled. Existing exposure uses the existing active monitor and independent
exit RPC fallback; entry simulation refreshes before/after latency.

RPC state is accepted only after owner/mint/market/slot/decode checks. Recovery
clears pending repair state and resets events_since_reconciliation/reconciled_at.
An older live/RPC slot cannot overwrite a known newer state. Same-slot receipt
ordering alone is not proof of transaction order: exact integer continuity is
checked and mismatches request reconciliation. time_since_reconciliation_ms is
unknown until a successful reconciliation; it is never initialized to zero.

This is a fail-safe partial bootstrap framework, not a completed canonical-identity
audit. Larger read-only synchronization acquisition can use it, but entry readiness
and percentage band calibration require the remaining identity/config proof.
