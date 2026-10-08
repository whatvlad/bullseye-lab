# Canonical identity bootstrap

Addresses are derived with solders' Solana PDA implementation, not custom elliptic-curve code. Official current IDLs are retained under `providers/solana/idl/` and SHA-256 pinned by `idl_schema.py`.

Pump.fun checks the `[bonding-curve,mint]` PDA, account/program ownership, native-SOL quote identity, completion state, mint address/owner/initialization/supply, canonical token-program-specific curve ATA, vault mint/authority/address and non-regressing account slots. Creator and fee/global references are retained. A complete curve requires migration recovery rather than curve execution. Unsupported quotes, ambiguous supply/bindings and legacy missing assumptions cannot become exact execution evidence.

PumpSwap checks `[pool,index_u16_le,creator,base_mint,quote_mint]` PDA and bump, base/quote orientation, canonical index-zero creator derived from Pump `[pool-authority,base_mint]`, both token-program-specific pool ATAs, vault mint/authority/address, initialized mint owners/addresses, a complete canonical source curve and its creator relationship. The virtual quote offset comes from the decoded pool account; it is added exactly once to the physical quote-vault balance. Arbitrary internally consistent pools are rejected as canonical.

The passive capture bootstrapped **12 Pump.fun curves** and accepted **11 reserve reconciliations**; one was rejected because the stream advanced beyond the RPC snapshot. Final stricter address guards were additionally validated on one curve and three PumpSwap pools. All three sampled pools pass canonical binding checks. These are sampled proofs at recorded read slots, not verification of every market.

At capture end, current canonical/config trust was zero: later unknown native invocations invalidated the cached proofs. `bootstrap_verified_by_venue` and current trust are separate fields in `analysis/identity_bootstrap.json`. A successful past bootstrap must not be presented as continuously verified identity.

Identity/config bootstraps are cached and invalidated by migration, owner/address/creator/offset mismatch or explicit/uncertain native updates. Trades never trigger per-event reads. Stable identity avoids the auxiliary mint/source-curve batch on subsequent reserve refreshes; config uses a shared four-account batch per generation. The observed uncertain-invocation/config churn still limits these potential savings.

Account batches are source-slot bounded, not transaction-boundary synchronized. Curve/vault reads at different slots cannot prove a historical reserved-inventory invariant; the report labels this limitation explicitly. Source wall-clock time is not invented from RPC receipt time.

Implementation: `providers/solana/canonical.py`, `bootstrap.py`, `paper/market_refresh.py`. [Official PumpSwap IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_amm.json), [official Pump IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json).
