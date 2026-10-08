# Telegram control panel

Phase 6 provides an English, button-driven Telegram control plane for Bullseye's
paper-only system. It never constructs, signs, or submits a Solana transaction.

## Access control

Access is default-deny. Configure numeric IDs in `.env`:

```dotenv
BULLSEYE_TELEGRAM_BOT_TOKEN=YOUR_BOTFATHER_TOKEN
BULLSEYE_TELEGRAM_ALLOWED_USER_IDS=[123456789]
```

`/whoami` is the only public command. It returns the sender's own numeric ID and
does not expose portfolio or system state. All messages and callback queries for
the control panel pass through the allowlist middleware.

Never paste the bot token into chat, logs, source, or Telegram messages.

## Processes

Run the market worker and bot separately:

```bash
bullseye discover
bullseye telegram
```

Both use PostgreSQL. The control table is the cross-process source of truth for:

- entry pause/resume;
- active strategy;
- position sizing;
- maximum positions;
- stop-loss, take-profit, and trailing-stop settings;
- watchlist and blacklist.

Pause stops new automatic entries. Existing paper-position exits remain active so
pause cannot silently disable risk management.

The dashboard presents this control as **Start trading / Stop trading**. The market
worker remains online in monitoring mode when trading is stopped. This lets it keep
market data current and manage protective exits, while preventing every new buy.

## Activity notifications

The discovery worker sends rate-limited messages to every allowed Telegram user for:

- active-strategy `watch` and paper-buy-candidate decisions;
- paper buy and sell fills, including amount, fees, price impact, and exit reason;
- rejected paper orders and the exact rejection reason;
- data-provider connection state changes.

Skip decisions from inactive strategies are intentionally not pushed because Solana
event volume would flood the chat. They remain available in the Signals panel and
database. Duplicate watch/candidate messages for the same mint are suppressed for 60
seconds by default. Notification delivery is isolated from execution: a Telegram
network failure cannot stop the paper-trading worker.

## Panels

- Dashboard: mode, active strategy, cash, cost basis, realized PnL, accounting, and
  provider health.
- Portfolio: report plus buttons for 100, 500, 1000, 2500, 10000, or custom capital.
- Positions: current paper positions with separate `Close on fresh trade` and
  warned `Force at last snapshot` controls. Queued closes show their timeout;
  forced stale fills disclose degraded quality and snapshot age.
  `Close all positions` pauses entries, requires confirmation, and supports both
  fresh-trade queued closes and forced closes from last known reserves.
- Strategies: Conservative, Balanced, Aggressive, and recorded comparison counts.
  Graduation velocity is an embedded score component in all three.
- Signals: latest `watch` and `enter_candidate` decisions.
- Outcomes: Phase 7 decision/trade counts, win/loss summary, skipped positive
  excursions, and recorded realized P&L.
- Wallets: ranked observed wallets, auditable alpha components, sample confidence,
  manual seed controls, and per-wallet evidence. Phase 8 scores are research-only.
- Settings: sizing, maximum positions, stop loss, take profit, and trailing stop.
- Manual paper: operator-requested simulated buy or full sell. Buys still require
  approved risk, current market evidence, available cash, and a non-blacklisted mint.
- Watchlist/blacklist: persistent token controls. Blacklisted tokens cannot open new
  automatic or manual paper positions.

Every manual result explicitly says that no real transaction was created.
Refreshing an unchanged panel is treated as a successful no-op, so repeated button
clicks do not produce Telegram `message is not modified` exceptions.

## Birdeye in Telegram

When configured, Birdeye REST is available for on-demand token enrichment. Calls
are cached for five minutes and globally spaced by at least 1.1 seconds for the
free Standard account. The Telegram UI does not continuously poll Birdeye.

## Operations

```bash
bullseye telegram-check
bullseye telegram --run-seconds 10
```

The bounded form is useful for startup smoke testing. `telegram-check` performs
only Telegram `getMe` and reports no token value.
