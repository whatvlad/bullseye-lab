# Forensic audit — 30 September 2026

Scope: existing Bullseye source, tests, migrations, configuration schema, local logs, saved research extracts and restored PostgreSQL. Inspection began 30 September and continued 1 October (Europe/Dublin). This is a paper research platform, not an existing live signer. No Axiom integration exists. No secrets are included here.

## Evidence and baseline

- Initial suite: 146 tests passed (Python 3.14 virtual environment).
- Initial PostgreSQL read: connection refused. After the operator started Docker, the original `bullseye-postgres-1` became healthy. Fresh repeatable-read snapshot: 18 portfolios, 225 positions, 215 outcomes, 499 filled orders and 238,314 market trades. No volume was recreated. Provider dashboards remain unavailable.
- Git has extensive pre-existing uncommitted/untracked work; preserve it. Git history contains only the initial scaffold. Do not attribute all existing source to this audit.
- `docs/incident-2026-09-17.ru.md`: 10 closed paper trades, −44.33 USDT on 100 USDT, 7.23 USDT recorded fees, two losses exceeding 60%. These figures require reconciliation against a database when available.

## Existing architecture

`memebot.cli` / `__main__` dispatch commands; `apps.worker` composes asyncio providers, PostgreSQL repositories, rolling features, bounded risk workers, multi-strategy decisions, paper execution, outcomes and wallet intelligence. `apps.telegram` runs a separate allowlisted control process communicating through PostgreSQL.

Discovery: PumpPortal launch/migration events when configured, otherwise official Pump/PumpSwap program log subscriptions. Decoders use pinned IDLs. HTTP RPC validates curves, mint state, pools and reserves. Primary HTTP and WebSocket URLs are independently configurable; exit reads have a fallback. Birdeye is optional candidate enrichment, DexScreener optional pool lookup, CoinGecko quote-currency conversion. No Jupiter, Jito sender, signer, real transaction simulation or submission exists. Network and priority costs are paper assumptions.

Storage: SQLAlchemy async PostgreSQL, Alembic migrations, SQLite tests. Durable domain events, tokens, trades, features, risks, strategies, decisions, pending actions, orders, portfolios, positions, outcomes, wallet profiles, experiments and controls. Redis absent. Event bus awaits handlers in order; risk queue and notification queue are bounded. Paper trade processing uses a separate worker. Money uses Decimal. Rolling windows use per-token deques. Configuration is Pydantic settings plus persistent trading controls and immutable strategy versions. Secrets use SecretStr and recursive log redaction.

## Token trace (source inspection; latency is not measured unless stated)

| Stage | Dependency / freshness | Failure, retry and fallback | Latency evidence |
|---|---|---|---|
| Launch → discovery | PumpPortal WSS or RPC logs; source and receive stamps | reconnect/resubscribe; account validation retries | distributions need recorded creation timestamps |
| Ingestion → registry | event bus + PostgreSQL; stable event UUID | transaction/uniqueness dedup; DB failure propagates | unmeasured; synchronous handler work can delay stream |
| Registry → observation | same trade stream; event-time rolling windows | late-event cutoff; absent wallet/reserves remain unknown | snapshots normally throttled to 1 second |
| Observation → risk | cheap flow filter then bounded RPC assessment | per-mint cooldown, hourly/daily local quota; critical unknown rejects | configured 10-second reassessment floor; RPC durations unmeasured |
| Risk → decision | MultiStrategyRunner; persisted risk/feature evidence | three immutable presets, reason codes, token-age gate | CPU stage unmeasured |
| Decision → quote | CoinGecko SOL/USD or derived SOL/USDT | cached timestamped reference; stale/failed quote rejects | external lookup/cache; unmeasured |
| Quote → paper buy | refreshed curve/pool reserves | price drift, signal expiry, cost/impact, exposure checks; pending TTL | default modeled 50+750 ms; actual settings differ |
| Buy → position | atomic order/portfolio projection | one open mint per portfolio; DB invariant guards | simulated fill, no on-chain confirmation |
| Position → monitoring | incoming trades + periodic RPC refresh | freshness gate; paused entries still allow exits | default 5-second monitor; event gaps are a risk |
| Exit → paper sell | same simulator; refreshed reserves + quote | stale/insufficient reserve rejection; pending manual close TTL | modeled latency, no transaction signature |
| Sell → net PnL | actual **simulated** proceeds and allocated cost basis | cash/cost/realized reconciliation; partial sells supported | no live wallet balance deltas available |

## Reproducible defects found before changes

1. **P0: Ollama replaces emergency exits.** `_evaluate_position` calls the model instead of the deterministic exit engine when configured. `hold` or an exception returns without honoring a hard stop. Execution-time price drift can also cancel a model sell during a crash. Reproduce with a position below stop plus model `hold`/timeout.
2. **P0: RPC response shape unvalidated.** `_call` casts response JSON to dict and calls `.get`; a JSON array/null leaks AttributeError rather than SolanaRpcError. JSON-RPC ID/version are unchecked. There is no transport cooldown, so a failed primary is retried on every fallback read.
3. **P0: incomplete close discards cost basis.** Registry accepts a CLOSE fill smaller than the open quantity then zeroes remaining quantity/basis. This violates the accounting identity. CLOSE must exhaust quantity; PARTIAL_CLOSE must preserve a positive remainder.
4. **P1: false API capability evidence.** Birdeye probe labels HTTP 400/404 as available, including potential authentication claims. An endpoint error is not evidence of entitlement.
5. **Research gap:** no standalone full deterministic session replay CLI. Existing rolling-feature tests are not proof of complete live/paper replay parity. Historical risk evidence must replay in arrival order, never be backfilled with future facts.

## Repairs and measured follow-up

All four reproduced defects were repaired with regression coverage. Ollama may refine only a deterministically eligible entry and cannot bypass blocking Alpha Filter evidence. Emergency stop, dump hazard and maximum holding time take precedence over model output/failure and are revalidated after execution delay. CLOSE must exhaust remaining quantity; invalid projection rolls back. Birdeye errors no longer claim entitlement. RPC envelopes are validated; 429/authorization/repeated failures open a bounded cooldown with Retry-After support, single recovery probe, metrics and primary/fallback separation. Entry decisions pause while the primary circuit is open.

Additional discovered defects: feature rolling buffers bounded time but retained **every inactive mint forever**; risk scheduling/lifecycle dictionaries likewise accumulated launches. Feature state now has a 10,000-mint LRU capacity with open-position pins, and risk history is bounded. Eviction telemetry makes lost observation context visible. PumpPortal source time was actually receipt time: new events explicitly mark it estimated, and launch-delay statistics exclude it. This is not a measured zero discovery delay.

Offline capture/loss analysis, causal decision replay and temporal feature analysis were added. The same current strategy runner generated byte-identical output twice for 1,693 real events from the two largest incident losses (222 decisions). This is decision replay using recorded risk/features, not on-chain transaction or fill replay. Paper buy evidence now records the modeled round-trip cost and a linear-proceeds break-even reference. Five-second forward labels were added prospectively; old missing labels stay missing.

## Existing safeguards and unresolved limits

Final verification: 170 tests passed; `ruff check src tests` passed; strict mypy passed across 96 application files; Docker PostgreSQL healthy and `memebot db-check` passed. Interim failures included a fractional-raw-unit test fixture, a manually calculated quote expectation and a Decimal accumulator type; these were corrected and the full checks rerun. Changes remain in the working tree: committing entire pre-existing untracked source files would mix unrelated user work into this audit.

Bounded current discovery smoke: 30 seconds, 26 real normalized launches, 28 lifecycle events, no paid token subscriptions and no database writes. All launch timestamps were receipt estimates, so actual creation-to-discovery latency remains unknown. This proves discovery transport/normalization only, not trading or paid-stream entitlement. PumpPortal connection health no longer labels every requested capability confirmed merely because a socket connects.

Final quote review found gross-budget percentage deduction in Pump.fun buys. It now uses fee-inclusive integer budgeting, separate rounded 95/30 bps fee components and the one-lamport curve adjustment from the official [buyExactSolIn IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.ts). This preserves the existing standard fee assumption; creator/global fee-config verification, canonical-pool verification, non-SOL markets and exact PumpSwap quotes remain unverified. Historical PnL was not rewritten using the new formula.

Prior September fixes already delay fills, revalidate reserves, enforce cost/impact limits, reserve loss budgets and pause mismatched experiments. Do not rewrite these or retune thresholds from ten losses. Stop prices are triggers, not guaranteed fills. Display marks and recorded MFE/MAE are not executable liquidation values. Funding clusters/bundled supply remain uncertain. SOL accounting is stored in raw fill amounts but USD/USDT remains the portfolio ledger. There is no proven out-of-sample edge. Live signing, full execution replay, concurrent independently funded profile portfolios and provider dashboard billing verification remain unfinished work. SHADOW explicitly labels hypothetical automatic orders and maintains the existing paper ledger; it does not establish equivalence to a live executor that does not exist. Provider seed/cache retention beyond the repaired feature/risk maps still needs a long-duration memory soak test.
