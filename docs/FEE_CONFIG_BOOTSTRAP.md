# Fee and config bootstrap

Four derived accounts were owner/address/discriminator validated and completely decoded at recorded slots: Pump Global, PumpSwap GlobalConfig, and the Pump fee-program FeeConfig PDAs for each venue. Every field, raw-account version hash and source slot is retained in `analysis/fee_config_bootstrap.json`.

VERIFIED_ONCHAIN inputs include initial curve reserves/supply, Pump fee and creator basis points, recipient lists, migration fee, Mayhem/cashback/holder-reward switches and authorities; PumpSwap LP/protocol/creator basis points, disable flags, recipients and boost authority/settings; and both fee-program flat/stable/exotic fee schedules and market-cap tiers. The captured Pump schedule has one dynamic tier and PumpSwap has 25. No basis points are copied into strategy thresholds or disagreement bands.

These account facts do **not** prove which schedule/tier, creator sharing or holder-reward/cashback route applies to a particular order at its historical instant. Per-curve configurable creator fees and Token-2022 extensions are not fully integrated. Exact executable rounding, network/priority fees, slippage and Mayhem/boost execution behavior remain unverified. Existing paper fee/slippage settings remain STATIC_ASSUMPTION, not VERIFIED_ONCHAIN execution. Missing per-market inputs are UNKNOWN.

The shared cache coalesces concurrent reads and hashes account bytes into version identifiers. An invalidation generation queues one refreshed four-account batch on the next admitted bootstrap/entry/exit duty; no trade invokes RPC. The passive run used 13 such batches amid native uncertainty. Failed or incomplete config decoding cannot yield an exact config version. Trailing schema omissions are retained as unknown fields, never silently filled into execution proof.

Observational reserve tracking does not require fee config. Reserves reconciled does not imply fee/config verified. Execution assumption verification stays false, so price evidence cannot be promoted to full execution trust merely because a config account decoded successfully. VERIFIED_ONCHAIN is a snapshot-at-slot fact, not a promise after unresolved updates.

Source schemas: [official fee IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_fees.json), [PumpSwap IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_amm.json). Implementation: `providers/solana/bootstrap.py`; schema versions are SHA-256 pinned in `idl_schema.py`.
