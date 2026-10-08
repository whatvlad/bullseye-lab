# Phase 8 wallet intelligence

Status: implemented; research-only trading influence

Phase 8 projects the wallet field already present in persisted Pump/PumpSwap trades.
It does not require a second real-time stream or consume additional Helius/Birdeye
credits. A bounded, idempotent backfill projects stored trades after migration.

## Evidence model

Every relevant wallet trade stores the wallet, token, side, raw amounts, event-time
price, slot, signature-linked event ID, and timestamp. Per-wallet/per-token outcomes
then track:

- first entry time and delay from launch;
- buy/sell counts and average-cost realized performance approximation;
- MFE, MAE, and time from entry to the configured +50% expansion;
- holding time when the observed balance is fully sold;
- graduation and deterministic liquidity-collapse exposure.

All observed wallets are retained, including losing and late entrants. Automatic
discovery does not begin from a hand-picked winner list.

## Alpha and confidence

The version-1 alpha hypothesis combines early-entry frequency, early-success
frequency, realized performance, adverse-selection safety, and consistency. Every
component is retained in `metrics_json`. Small samples shrink toward neutral 50:

```text
adjusted alpha = 50 + (raw alpha - 50) × min(sample size / 20, 1)
```

Default lifecycle:

- `observed`: any wallet in the relevant event stream;
- `candidate`: at least 3 launches and at least 2 early +50% expansions;
- `scored`: at least 10 launch samples;
- high confidence: at least 30 launch samples.

These thresholds are configurable. Manually tracking a wallet adds a label,
real-time Pump/PumpSwap BUY/SELL alerts, an observed activity feed, and local
portfolio analytics. It does not grant a high score or trading authority.

## Manual wallet tracking

Open **Wallets** in Telegram, press **Track wallet**, and send a Solana wallet
address followed by an optional label on the same line. Bullseye then reports newly
observed Pump.fun/PumpSwap buys and sells with token, SOL amount, timestamp, and a
Solscan transaction link.

The wallet detail screen shows:

- latest observed actions;
- open token count;
- aggregate observed realized, unrealized, and total P&L in SOL;
- per-token open/closed state and P&L;
- entry timing, win rate, drawdown, rug exposure, and confidence.

Valuation is reconstructed from events observed while Bullseye is running. It is
not an authoritative on-chain balance statement: activity before observation,
transfers, and swaps on unsupported venues can make the reconstructed inventory
incomplete.

## Boundaries

- Wallet scores cannot approve, reject, size, or exit a trade in Phase 8.
- Alerts do not copy a tracked wallet's transaction.
- Live tracking currently covers Pump.fun and PumpSwap events in Bullseye's market
  stream. Arbitrary Jupiter, Raydium, Orca, and direct token transfers require a
  future address-specific transaction stream and are not represented yet.
- Funding relationships, wallet clusters, and independent consensus belong to Phase 9.
- Unknown entry timing and incomplete realized histories remain unknown.
- Helius Wallet API history is not required. It remains an optional future enrichment
  because the current API is beta and each request has a credit cost.

## Commands

```powershell
bullseye wallets --limit 20
bullseye wallet <ADDRESS>
bullseye wallet-seed <ADDRESS> --label "Research wallet"
bullseye wallet-unseed <ADDRESS>
bullseye wallet-backfill --limit 2000
```

The CLI retains the historical `seed` naming internally. Telegram presents the
same operation as **Track wallet** / **Stop tracking**.
