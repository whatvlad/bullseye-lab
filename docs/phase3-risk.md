# Phase 3 token risk engine

Status: implemented  
Execution boundary: analytics only; no orders, signing, swaps, or private keys

## Decision contract

Each `TokenRiskAssessed` event contains:

- `allowed=true`, `false`, or `null` when critical facts are unknown;
- a 0–100 risk score only when critical evidence is complete;
- stable hard-reject and warning reason codes;
- explicit critical unknown categories;
- every evaluated value, threshold, availability, message, provider, observation
  time, confidence, and source slot.

An RPC failure is not a safe result. If mint security, adjusted holder
distribution, liquidity, or market validation cannot be established, the risk
gate does not approve the token. A separately proven hard reject still produces
`allowed=false` even when other facts are missing.

## Standard-RPC evidence

Phase 3 uses vendor-neutral Solana JSON-RPC calls available through the configured
Helius endpoint:

- SPL/Token-2022 mint prefix for supply, initialization, mint authority, and
  freeze authority;
- largest token accounts plus decoded account owners;
- creator-owned token accounts;
- Pump bonding-curve or PumpSwap pool accounts and quote reserve accounts.

Market-controlled balances are removed before holder concentration is computed.
For PumpSwap, the pool base-token account is excluded explicitly. For bonding
curves, token accounts owned by the validated curve address are excluded.

Effective quote liquidity includes the protocol's decoded virtual quote reserve.
Amounts remain raw integers because Phase 3 compares presence and concentration;
it does not invent USD values.

## Initial deterministic policy

Default hard rejects:

- mint authority remains enabled;
- freeze authority remains enabled;
- mint is not initialized;
- deterministic market validation is rejected;
- largest non-market holder owns at least 40% of circulating supply;
- creator owns at least 20% of circulating supply;
- effective quote liquidity is zero.

Default warnings include top-five/top-ten concentration, a largest early buyer
with at least 50% of observed early buy volume, three or more distinct buyers in
one slot, and prior rejected markets from the same observed creator. Thresholds
are typed `BULLSEYE_RISK_*` settings and are included in evidence.

## Wallet-cluster boundary

Phase 3 adds two conservative local signals from the first 200 observed buys:
largest buyer share and same-slot buyer grouping. These are signals, not proof of
common control. Standard snapshot RPC does not prove a wallet funding graph or
bundled launch supply, so both remain explicit unknown evidence instead of being
guessed.

## Operations

Risk collection runs in a bounded queue with a fixed worker count so HTTP account
lookups cannot create unbounded work behind WebSocket ingestion. Assessments have
deterministic IDs derived from their lifecycle trigger and are idempotently
stored in PostgreSQL.

```powershell
bullseye db-upgrade
bullseye discover
bullseye risk <mint> --limit 1
```

`bullseye token <mint>` also includes the latest risk assessment. Phase 3 does
not claim that the thresholds predict returns; it establishes an auditable safety
boundary for Phase 4 strategy experiments and later paper execution.
