# Architecture

## Current review — 1 October 2026

The sections below describe the historical Phase 5 baseline. The current implementation also includes wallet intelligence, outcome recording, experiments, Alpha Filter, optional Ollama, Pulse, restart recovery and persistent pending paper actions. See [the forensic audit](AUDIT.md) for verified defects and [the runbook](RUNBOOK.md) for current checks.

```text
Pump/PumpSwap logs OR PumpPortal launch/trade stream
  → normalized immutable events → ordered async bus → PostgreSQL evidence
  → bounded rolling token state → cheap flow filter
  → bounded candidate-only on-chain risk collection
  → MultiStrategyRunner (Conservative / Balanced / Aggressive)
  → optional Ollama refinement (eligibility/risk cannot be bypassed)
  → Pulse + Alpha + portfolio risk + freshness + cost/impact guards
  → delay → refreshed reserves → revalidation → paper/shadow fill
  → atomic position/cash ledger → event/periodic exits → net PnL/outcomes
```

HTTP RPC health/cooldown and exit fallback are separate from the WSS reconnect loop. The primary circuit pauses entry decisions; fallback is an emergency read path, not a way to evade an account quota. RPC metrics count transport requests by method, failures by code and recent request latency. Runtime metrics emit every 30 seconds with the portfolio reconciliation report. Latency samples and feature states have explicit bounds; open positions pin their feature state. The registry/outcome tables remain the durable evidence source.

Modes: PAPER simulates reserve-based fills; SHADOW uses the same decision/risk/execution path and records `shadow_only` hypothetical automatic orders plus `would_buy`/`would_sell` logs. Use a dedicated experiment portfolio for each mode. REPLAY is an offline **decision** CLI using the same MultiStrategyRunner and only previously received evidence. It does not replay reserve refresh calls, Ollama choices or fills. LIVE is rejected by settings. There is no signer, Jito sender or hidden transaction path.

Canonical state is split between `tokens` (identity/lifecycle), rolling feature state, risk snapshots and durable paper positions. This avoids replacing functioning structures with a second TokenState class. Unknowns remain typed unknown observations; third-party reception timestamps are explicitly estimated. State evictions require a new observation period and do not manufacture historical windows.

Production database schema and trading controls were read, not reset, during the audit. Existing phase notes are retained below for history.

Status: Phase 5 realistic paper trading and portfolio accounting  
Last reviewed: 2026-08-22

## Purpose and constraints

Bullseye Lab is an experimental Solana memecoin research platform. Its job is to
capture enough reliable evidence to determine whether strategies have positive
expectancy after realistic costs. It is not a latency-sniping project and a high
win rate is not its objective function.

The initial product is forward paper trading. There is no transaction signing,
private-key configuration, swap submission, or hidden live mode. A future live
execution milestone would require separate authorization and an isolated signer.

V1 is Solana-only. Provider interfaces avoid vendor coupling but do not introduce
premature multi-chain abstractions.

## System shape

```text
Official API / Solana RPC
          |
          v
  Provider adapters  -- capability probe / health / reconnect
          |
          v
  Normalize + validate timestamps, provenance, identifiers
          |
          v
  Deterministic async event bus
          |
          +--> token registry + lifecycle persistence
          +--> rolling market state and feature engine        (Phase 2)
          +--> bounded on-chain collection + risk rules       (Phase 3)
          +--> versioned strategy decisions                   (Phase 4)
          +--> realistic paper execution + portfolio ledger  (Phase 5)
          +--> taken and skipped outcome recorders            (Phase 7)
```

The first deployment is one asyncio process plus PostgreSQL. The event bus is
in-process and awaits handlers in registration order; it creates no hidden tasks.
This makes failures visible and replay deterministic. Redis Streams or another
transport should only be introduced when a measured need for cross-process
durability or scaling exists.

## Package boundaries

| Package | Responsibility through Phase 3 |
| --- | --- |
| `memebot.core` | typed settings, UTC/monotonic clock, structured logging |
| `memebot.models` | provider-provenanced observations and core market/risk contracts |
| `memebot.events` | immutable, versioned events and deterministic dispatch |
| `memebot.providers` | read-only RPC/WSS, pinned Pump decoding, validation, reconnect |
| `memebot.intelligence.features` | bounded event-time windows and deterministic metrics |
| `memebot.intelligence.risk` | on-chain evidence collection, wallet signals, deterministic risk policy |
| `memebot.strategies` | transparent scoring, regime classification, versioned decision-only presets |
| `memebot.paper` | paper fills, latency/fee assumptions, sizing, positions, exits, accounting |
| `memebot.storage.database` | async engine, migrations, idempotent token/lifecycle projection |
| `memebot.apps` | composition roots; no strategy logic or provider-specific code |

Later features get separate packages only when their phase starts. Empty
directories for all fourteen future phases would create false architecture and
are intentionally not scaffolded.

## Event contract and time

Every event has:

- an immutable UUID;
- a discriminated event type and schema version;
- the source event timestamp;
- the provider-received timestamp when available;
- the local ingestion timestamp;
- provider identity;
- optional source signature, slot, sequence, and correlation identifiers.

All wall-clock timestamps must be timezone-aware and are normalized to UTC.
Naive timestamps fail validation. Latency measurement uses an injectable
monotonic clock; wall-clock ordering is never used to measure elapsed time.

The core event contract currently includes:
`TokenDiscovered`, `TokenTrade`, `TokenLifecycleChanged`,
`ProviderHealthUpdated`, `MarketFeatureSnapshotCreated`, and
`TokenRiskAssessed`, `StrategyDecisionCreated`, and `PaperOrderCompleted`. Later phases extend the discriminated union with new schema
versions rather than putting arbitrary dictionaries on the event bus.

## Unknown and degraded data

`Observation[T]` separates the value from availability, confidence, timestamps,
and provider. `unknown` and `unavailable` require a reason and cannot carry a
value. `stale` can retain the last value but consumers must make an explicit
decision to use it. Missing values are never silently converted to zero.

Provider capabilities are likewise `confirmed`, `unavailable`, or `unknown`.
Plan names and documentation are hints, not proof of account entitlement. Each
adapter will probe safe endpoints/streams at startup and report the result.

## Storage approach

PostgreSQL is the production database. SQLAlchemy 2.x async sessions and Alembic
migrations are the only application path. SQLite is used only for fast isolated
tests.

The Phase 0 and Phase 1 migrations create:

- `tokens`: canonical Solana token identity and validation state;
- `markets`: venue/pool identity attached to a token;
- `domain_events`: versioned normalized evidence with event-ID deduplication;
- `provider_health`: current capability and connection status.
- `token_lifecycle_events`: append-only curve, final-stretch, graduation, and
  post-graduation observations.
- `token_trades`: normalized Pump/PumpSwap transactions with raw amounts;
- `market_feature_snapshots`: reproducible multi-window feature state.
- `token_risk_assessments`: append-only decisions, reasons, warnings, unknowns,
  thresholds, values, and provenance.
- `strategy_configurations`: immutable versioned preset parameters and weights;
- `strategy_decisions`: append-only scores, regimes, actions, component evidence,
  and the exact risk/feature event references used at decision time.
- `paper_portfolios`: starting cash, current cash, currency, and realized PnL;
- `paper_positions`: quantity, remaining cost basis, peaks, partial-exit state, and
  close state;
- `paper_orders`: filled and rejected attempts with complete timing/fill evidence.

`tokens` also carries current lifecycle, current market, last source slot, and
graduation time. Source-slot checks prevent late WebSocket notifications from
regressing current token state; all observations remain in event history.

The full logical model will later add deeper wallets and clusters, strategies and
versions, decisions, paper orders/fills/positions, outcomes, social events, LLM
analyses, and experiment runs. These are described now but not created before
their owning phase.

High-frequency provider payloads will not be retained forever in ordinary OLTP
tables. The intended retention layers are:

1. short-lived raw normalized events for incident diagnosis and replay;
2. rolling/aggregated snapshots for efficient features;
3. immutable decision-time snapshots for reproducibility;
4. long-lived outcomes and research rows.

Retention and partitioning will be sized from observed Phase 1 volume before a
specific policy is chosen.

## Provider ingestion rules

Each adapter owns transport concerns: timeouts, heartbeat, exponential backoff
with jitter, resubscription, rate limits, and payload validation. It emits only
normalized events. Adapters cannot write strategy or portfolio state directly.

Event identifiers prefer a stable provider identifier (for example a Solana
signature plus instruction/log index) when available. If a provider supplies no
stable ID, the adapter must document its deterministic deduplication key. Database
uniqueness is the final idempotency guard.

Phase 1 implements the canonical on-chain discovery path:

1. two `logsSubscribe` subscriptions for the official Pump and PumpSwap program
   IDs;
2. pinned Anchor event decoding and deterministic normalization;
3. HTTP `getAccountInfo` validation of curve, pool, and pool reserve accounts;
4. ordered projection into PostgreSQL.

Helius/Solana RPC remains the canonical real-time on-chain path. Phase 6 adds an
official Birdeye REST adapter for capability probing and cached, on-demand market
enrichment. The verified free Standard account has 30,000 CU and no WebSocket
entitlement, so Birdeye is not polled for every event and never replaces missing
on-chain evidence with synthetic values.

## Paper execution boundary

Phase 5 has a paper-only simulator behind the strategy/risk boundary. It uses the
latest evidence available at paper-decision time, models constant-product price
impact from decoded venue reserves, and records explicit fee/latency assumptions.
It cannot access a signer, construct a transaction, or submit a swap. Future
outcome prices are never used to create an entry fill.

Any eventual `ExecutionProvider` will be a separate future milestone. Strategy
code will never hold signing material.

## Security

- Configuration exposes no private-key or signer field.
- Secrets use Pydantic `SecretStr` and safe summaries contain booleans, not values.
- The logging pipeline redacts known credential fields recursively.
- Provider payloads are validated before entering core modules.
- Telegram access control requires an explicit allowed-user-ID set and defaults to deny.
- External I/O will use bounded timeouts and response-size limits in its owning phase.

## Local environment findings

The repository began with only a README and `.gitignore`. The active environment
uses Python 3.14 and Docker Desktop with PostgreSQL 17. Redis remains unnecessary.

## Decisions

1. **Modular monolith first.** One process keeps event ordering, replay, and local
   operations understandable. Split only after measurement.
2. **PostgreSQL without Redis in Phase 0.** Redis currently has no justified job.
3. **Pydantic at trust boundaries; SQLAlchemy in storage.** Transport/domain
   validation and persistence concerns remain separate.
4. **Decimal for money and quantities.** Provider parsing will convert decimal
   strings directly, never through binary float.
5. **Capability discovery over tier assumptions.** This handles API plan changes
   and the current Birdeye documentation inconsistency.
6. **No Axiom adapter.** No supported developer API was verified in official
   documentation as of the review date.
7. **No premature ML or LLM coupling.** Rules/statistics come first; the future
   LLM remains outside the critical path.

## Phase 7 entry criteria

- The Phase 2 replay suite produces identical output for identical evidence.
- PostgreSQL migration and bounded live feature ingestion pass.
- Paper cash plus remaining position cost basis equals initial cash plus realized
  PnL after every projected fill.
- Missing/stale price or reserve evidence rejects execution rather than fabricating
  a fill.
- No private-key, signing, transaction-building, or swap-submission dependency exists.
- Telegram mutations are durable, allowlisted, and visible to the worker across processes.
- Helius remains operational when Birdeye is unavailable or its CU budget is exhausted.
