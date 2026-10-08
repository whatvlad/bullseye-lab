# Bullseye Lab

The [1 October forensic audit](docs/AUDIT.md) includes reproduced safety repairs,
[all-portfolio loss statistics](docs/LOSS_ANALYSIS.md),
[API bottlenecks](docs/API_MATRIX.md), [cost scenarios](docs/COSTS.md),
[strategy evidence](docs/STRATEGY_ANALYSIS.md) and an updated [runbook](docs/RUNBOOK.md).
The platform remains paper/shadow only; [live readiness is blocked](docs/LIVE_TRADING_CHECKLIST.md).
Offline decision replay uses the same strategy runner and recorded causal evidence,
but does not yet replay fills or prove a profitable edge.

Bullseye Lab is a Solana memecoin research and automated **paper-trading**
platform. It is built in explicit phases so data quality, execution realism, and
statistical evidence come before strategy optimization.

## Current paper baseline — 0.2.0 / Aggressive v10

The active sizing profile is now [adaptive $10–40% paper sizing](docs/adaptive-sizing.ru.md).
Market data uses the [continuous metered PumpPortal mode](docs/continuous-paid-data.ru.md).
The September 16 paper revision activates Aggressive v10, admits earlier distributed
buying, lowers the New Pairs Pulse market-cap floor to $5,000, and allows a
12-second decision-to-fill interval with fresh-price revalidation. See
[the sniper paper revision](docs/sniper-paper-v10.ru.md) for the observed funnel
and operating instructions.

The September 13 corrections replace premature fills, inconsistent trade-average
marks, oversensitive dump-hazard exits and uncalibrated score-based sizing.
Runtime execution now waits for configured latency, refreshes reserves and
revalidates the trade. Balanced tests early demand; Conservative separately tests
post-graduation continuation. The active portfolio is controlled by the database.

See [the implementation and operating notes](docs/sniper-v9-implementation.ru.md)
for exact parameters, verification and limits. Earlier phase descriptions below
are historical; the new notes describe the current baseline. This remains paper
execution only, with no transaction signing or submission.

Phase 9A adds a research-derived graduation-velocity component to every strategy and realistic
Pump/PumpSwap fees to the existing forward paper-trading system. It retains the
allowlisted English Telegram control panel, read-only Helius discovery,
evidence-backed risk, and versioned strategy decisions. The application cannot
sign or submit a Solana transaction and contains no real-money execution mode.

## What exists through Phase 10A

- Python 3.13+ package using a `src/` layout.
- Typed environment configuration with redacted credentials.
- UTC-aware immutable domain events and deterministic async dispatch.
- Vendor-neutral Solana JSON-RPC and WebSocket clients.
- Pump/PumpSwap creation, trade, curve-completion, and migration decoding from
  pinned official IDLs.
- Automatic reconnect/resubscription with exponential backoff and jitter.
- On-chain curve/pool validation, duplicate-safe token registry, lifecycle
  history, and provider-health persistence.
- Normalized Pump and PumpSwap trade ingestion with durable raw on-chain amounts.
- Event-time rolling windows for 1s, 5s, 10s, 15s, 30s, 60s, 2m, 5m, and 10m.
- Volume, buy/sell flow, unique traders, price velocity, reserve velocity,
  buyer-volume concentration, robust sell outliers, acceleration, and lifecycle
  feature snapshots.
- SPL mint/freeze authority checks, market-adjusted holder concentration,
  creator holdings/history, and effective curve/pool liquidity checks.
- Deterministic hard rejects, warnings, explicit critical unknowns, and complete
  evidence/provenance on every risk assessment.
- Initial early-buyer concentration and same-slot wallet grouping signals. Funding
  attribution and bundled-supply claims remain explicitly unknown.
- Transparent momentum, wallet, risk, social, lifecycle, and market score
  components with unavailable inputs preserved as unavailable.
- Deterministic regime classification and independently versioned Conservative,
  Balanced, and Aggressive decisions, each with integrated graduation velocity.
- Multi-strategy comparison on every eligible risk assessment. Aggressive is the
  default active preset, but Phase 4 emits decisions only and cannot place orders.
- Configurable USD/USDT paper portfolios with exact cash, cost-basis, realized
  PnL, and reconciliation invariants.
- Constant-product Pump/PumpSwap fill simulation using decision-time reserves,
  position-size price impact, the official 1.25% Pump fee and market-cap-tiered
  canonical PumpSwap fees, priority/network cost, and simulated latency.
- Automatic active-strategy paper entries plus stop-loss, dump-hazard,
  partial-take-profit, trailing-stop, and maximum-holding-time exits.
- Strategy-independent portfolio risk governor with fixed score-independent base
  sizing, exposure and daily-loss caps, reserved worst-case stop risk, automatic
  equity circuit breaker, cooldowns, and one-open-position-per-mint DB guard.
- Keyless CoinGecko SOL/USD and derived SOL/USDT reference pricing with timestamps
  and staleness rejection.
- Official Birdeye REST capability probing and CU-conscious, on-demand token market
  enrichment. Helius is retained for candidate-only on-chain RPC validation.
- Metered PumpPortal discovery with free launch/migration events, short-lived
  candidate trade subscriptions, optional local spending cap, and RPC validation fallback.
- Candidate-only Alpha Filter with a global memecoin regime, local deployer history,
  budgeted Birdeye dev/insider/bundler/sniper cohorts, and explicit shadow evidence.
- Strategy-specific reserve-based entry price-impact limits instead of a fixed
  market-cap cutoff, plus a Telegram daily journal with PnL, MFE/MAE, exits, and
  rejection reasons.
- English Telegram dashboard with buttons for portfolios, positions, strategy
  selection/comparison, runtime paper settings, signals, pause/resume, manual paper
  orders, confirmed close-all, watchlist, blacklist, and manual Pump/PumpSwap wallet
  tracking with BUY/SELL alerts and observed P&L analytics.
- Default-deny Telegram access control using explicit numeric user IDs. `/whoami`
  reveals only the sender's own ID so the allowlist can be configured safely.
- SQLAlchemy async models, PostgreSQL, and Alembic migrations.
- Diagnostic, discovery, token-inspection, and provider-health CLI commands.
- Structured logging with recursive credential redaction.

Outcome recording, deeper wallet funding intelligence, social ingestion, and LLM
analysis belong to later phases.

## Requirements

- Python 3.13 or newer.
- PostgreSQL 16+ for runtime.
- Docker Desktop is optional and can run the supplied local PostgreSQL service.

Redis is not required. It will be introduced only if later measurements justify
cross-process transport or caching.

## Local setup

PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Linux/macOS:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
```

## Database

With Docker Desktop running:

```bash
docker compose up -d postgres
bullseye db-upgrade
bullseye db-check
```

Alembic migrations are the production schema path. Direct `create_all()` exists
only for isolated tests.

## Solana configuration

Copy the complete mainnet HTTP and WebSocket provider URLs into `.env`. With
Helius, the API key is already embedded in each URL; there is no separate Helius
key setting.

```dotenv
BULLSEYE_SOLANA_RPC_HTTP_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
BULLSEYE_SOLANA_RPC_WS_URL=wss://mainnet.helius-rpc.com/?api-key=YOUR_KEY
BULLSEYE_SOLANA_EXIT_RPC_HTTP_URL=https://api.mainnet-beta.solana.com
BULLSEYE_SOLANA_COMMITMENT=confirmed
```

The exit URL is a low-volume emergency read path for open paper positions. It is
not used for global discovery. Repeated provider `InvalidStatus` responses pause
new entries and reduce reconnect attempts to one probe every 15 minutes.

Never share these complete URLs. `bullseye show-config` reports only the hostname.
Tests need no external credentials.

Check the configured read-only RPC:

```bash
bullseye rpc-check
```

## Birdeye configuration

The free Standard plan currently provides 30,000 CU per billing cycle and a
1-request/second account limit. Bullseye therefore does not poll Birdeye for every
on-chain event. Helius handles continuous Pump/PumpSwap discovery; Birdeye REST is
used on demand and cached for token market enrichment.

```dotenv
BULLSEYE_BIRDEYE_API_KEY=YOUR_KEY
BULLSEYE_BIRDEYE_MINIMUM_INTERVAL_SECONDS=1.1
BULLSEYE_BIRDEYE_CACHE_SECONDS=300
BULLSEYE_BIRDEYE_MONTHLY_CU_BUDGET=25000
```

Probe the account without exposing its key:

```bash
bullseye birdeye-check
```

The verified Standard account supports credits, network discovery, token price,
token market data, and new-listing REST calls. Continuous Birdeye WebSockets are
not used because the official package matrix reserves them for Premium and above.

## Run discovery and features

Start the foreground worker:

```bash
bullseye discover
```

Stop with `Ctrl+C`. For a bounded smoke test:

```bash
bullseye discover --run-seconds 30
```

Inspect persisted state:

```bash
bullseye provider-health
bullseye token <SOLANA_MINT_ADDRESS>
bullseye features <SOLANA_MINT_ADDRESS> --limit 1
bullseye risk <SOLANA_MINT_ADDRESS> --limit 1
bullseye strategies
bullseye decisions <SOLANA_MINT_ADDRESS> --limit 10
bullseye portfolio
bullseye paper-orders --limit 20
bullseye outcome-summary
bullseye decision-outcomes --limit 20
bullseye trade-outcomes --limit 20
bullseye wallets --limit 20
bullseye wallet <SOLANA_WALLET_ADDRESS>
bullseye wallet-seed <SOLANA_WALLET_ADDRESS> --label "Research wallet"
bullseye wallet-unseed <SOLANA_WALLET_ADDRESS>
bullseye wallet-backfill --limit 2000
```

The worker subscribes to official Pump and PumpSwap program logs, validates
referenced accounts over HTTP RPC, and persists deterministic normalized events.
Replayed notifications do not create duplicate tokens.

Stale but otherwise valid paper entries wait briefly for the next fresh trade
instead of being discarded. Manual closes can either wait for fresh reserves or,
after an explicit warning, use the last snapshot as a degraded paper fill. See
[paper trading](docs/paper-trading.md).

Create a fresh active paper portfolio without deleting historical portfolios:

```powershell
bullseye portfolio-create --name "Experiment 2" --capital 2500 --currency USDT
```

For comparable baseline data, use an isolated experiment instead of a free-form
portfolio. Entries must be paused and all positions closed before it starts:

```powershell
bullseye entries-pause
bullseye sizing-set --base 8 --max 8
bullseye risk-set --stop-loss 12 --max-open-positions 5
bullseye experiment-start --name baseline-v1 --capital 100 --currency USDT
bullseye experiment-report --name baseline-v1
bullseye experiments
```

The experiment stores an immutable, secret-free snapshot of settings, persistent
trading controls, strategy version, application version, and its dedicated
portfolio. The worker keeps paper entries paused when no matching active experiment
exists. `experiment-stop` also requires every position to be closed. Old mixed-run
data is retained outside the experiment boundary as pre-baseline history.

Experiment reports include expectancy, profit factor, drawdown, P&L with the largest
winner removed, execution fees, rejection causes, score/regime counts, and p50/p95
latency. Paper fills include the configured PumpPortal Local API service fee in
addition to Pump/PumpSwap venue and Solana network fees.

The daily-loss guard is fail-closed: an observed equity breach automatically pauses
new entries. Before every buy it also reserves the configured worst-case loss for
all open positions plus the candidate order. Strategy v8 requires distinct buyers
and rejects entries whose scoring-window price rise is already beyond the preset's
anti-chase limit. Until score buckets show calibrated forward returns, score controls
eligibility but does not increase allocation.

## Telegram control panel

Add the BotFather token and an explicit numeric allowlist:

```dotenv
BULLSEYE_TELEGRAM_BOT_TOKEN=YOUR_BOTFATHER_TOKEN
BULLSEYE_TELEGRAM_ALLOWED_USER_IDS=[123456789]
```

If you do not know your ID, run `bullseye telegram`, send `/whoami` to the bot,
then add the returned number to `.env` and restart the bot. Every other action is
denied until the allowlist is configured.

```bash
bullseye telegram-check
bullseye telegram
```

Run `bullseye discover` in a second terminal. Telegram and the worker coordinate
through PostgreSQL, so pause/resume, strategy selection, risk/sizing settings,
watchlist, and blacklist changes take effect without sharing process memory.

When `BULLSEYE_OLLAMA_MODEL=qwen3:14b` is set, local Ollama makes the active
paper strategy's buy/skip decision, chooses a 10–40% allocation, and decides
whether to hold, sell, or partially sell an open position. The deterministic
strategies remain as research comparisons. Invalid, timed-out, or unavailable
model responses cannot create entries or exits. The paper execution layer still
checks market freshness, fees, liquidity, cash, and portfolio loss limits.
Pulse filters remain the configured candidate universe. Start Ollama before the
worker and check it without placing an order with
`$env:PYTHONPATH='src'; .venv\Scripts\python.exe docs\smoke_ollama_policy.py`.
The worker does not automatically unpause an experiment after a settings/code
change or an RPC quota outage.

Under **Wallets**, use **Track wallet** to add a Solana address and optional label.
The market worker will alert on newly observed Pump.fun/PumpSwap trades and build a
local activity/P&L report. This is observation only, never automatic copy trading;
other venues and activity before Bullseye started are not included yet.

## Tests and quality checks

```bash
pytest
ruff check .
mypy src
```

Tests use async SQLite for fast isolation and migration coverage. Runtime smoke
validation uses the local PostgreSQL service.

## Documentation

- [Architecture](docs/architecture.md)
- [Data sources and access tiers](docs/data-sources.md)
- [Phase 1 discovery operations](docs/phase1-discovery.md)
- [Phase 2 market features](docs/phase2-features.md)
- [Phase 3 token risk engine](docs/phase3-risk.md)
- [Transparent scoring](docs/scoring.md)
- [Versioned strategies](docs/strategies.md)
- [Paper trading](docs/paper-trading.md)
- [Telegram control panel](docs/telegram.md)
- [Phase 7 outcome recorder](docs/phase7-outcomes.md)
- [Phase 8 wallet intelligence](docs/phase8-wallets.md)

## Phase status

- Phase 0: foundation and provider research — implemented.
- Phase 1: on-chain Pump/PumpSwap discovery — implemented.
- Phase 2: rolling market state and feature engine — implemented.
- Phase 3: evidence-backed token risk engine — implemented.
- Phase 4: scoring and multi-strategy decisions — implemented.
- Phase 5: realistic paper trading and accounting — implemented.
- Phase 6: Telegram control panel and Helius + Birdeye integration — implemented.
- Phase 7: taken/skipped outcome recorder and trade lifecycle analytics — implemented.
- Phase 8: empirical wallet intelligence and automatic discovery — implemented.
- Phase 9: wallet graph and independent smart-money consensus — next.

The project is a research platform first. A process running without errors is not
evidence of a trading edge.
