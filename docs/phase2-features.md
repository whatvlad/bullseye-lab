# Phase 2 market state and feature engine

Status: implemented  
Execution boundary: analytics only; no orders, signing, or swaps

## Input and persistence

Official Pump `TradeEvent` and PumpSwap `BuyEvent`/`SellEvent` records are decoded
from the same pinned IDLs used in Phase 1. Only trades for known curve or pool
identities enter the feature engine. Active identities are restored from
PostgreSQL after a worker restart.

Amounts are stored exactly as raw on-chain integers. They are not silently
presented as SOL, USD, or UI token units without verified decimal metadata.
`price_raw = quote_amount_raw / token_amount_raw`; its relative change and
velocity are valid for the same market because decimal scaling is constant.

## Windows

Default event-time windows:

```text
1s, 5s, 10s, 15s, 30s, 60s, 120s, 300s, 600s
```

Override them with `BULLSEYE_FEATURE_WINDOWS_SECONDS`. Windows must be sorted,
unique, positive, and no longer than one hour.

Each token holds only the maximum configured window in memory. Events are ordered
by source timestamp, slot, and immutable event ID. Duplicate IDs are ignored.
Events arriving more than `BULLSEYE_FEATURE_MAX_LATENESS_SECONDS` behind the
current watermark remain in durable trade evidence but do not rewrite previously
published snapshots.

## Snapshot metrics

Every window contains:

- buy, sell, and total transaction counts;
- raw buy/sell/total quote volume;
- unique buyers and sellers;
- average, median, and largest trade sizes;
- buy/sell count and volume ratios;
- normalized flow imbalance `(buy - sell) / total`;
- open/close raw price and percentage price change;
- price velocity and price acceleration;
- volume velocity and acceleration;
- transaction-rate acceleration;
- unique-buyer-rate acceleration;
- buy-pressure acceleration.

Acceleration compares the recent and previous halves of a window. For a value
rate `v`, acceleration is `(v_recent - v_previous) / half_window_seconds`.
Missing denominators produce `null`, not invented zero ratios.

Snapshots also include current lifecycle, validation state, lifecycle age,
bonding progress, and market identity. The default cadence is at most one trade-
triggered snapshot per token per event-time second; lifecycle changes force a
snapshot immediately.

## Commands

Run the same worker used in Phase 1:

```powershell
bullseye discover
```

Inspect the latest feature state:

```powershell
bullseye features <mint> --limit 1
```

`bullseye token <mint>` also includes its latest snapshot.

## Reproducibility and anti-lookahead

The feature engine uses only normalized events with source timestamps at or
before the current watermark. Snapshot IDs derive from the triggering immutable
event. Given identical ordered events and configuration, the complete serialized
snapshot sequence is identical. Future prices and outcome data are not inputs.

Phase 2 does not claim predictive value. It creates auditable evidence for Phase
3 risk analysis and later strategy experiments.
