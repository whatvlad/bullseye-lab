# Runbook — current paper/shadow platform

Run commands from the repository root using the existing virtual environment. No private key is required or supported. Local date of this review: 1 October 2026, Europe/Dublin. Database/event timestamps use UTC.

## Database recovery

The existing Docker service and original volume were found healthy after Docker Desktop started. No database was created, recreated, migrated or reset during this audit. Docker is not on the current shell PATH; on this machine the executable is:

```powershell
& "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe" compose ps -a
```

If the service is absent, `docker compose up -d postgres` uses the supplied named volume. Inspect volumes/backups first. Never use `down -v` as a recovery step. Apply `bullseye db-upgrade` only to the intended database; a fresh database has no historical trades.

## Read-only diagnostics

```powershell
.venv\Scripts\python.exe -m memebot doctor
.venv\Scripts\python.exe -m memebot rpc-check
.venv\Scripts\python.exe -m memebot provider-health
.venv\Scripts\python.exe -m memebot portfolio
.venv\Scripts\python.exe -m memebot experiment-report
.venv\Scripts\python.exe -m memebot.research.capture --output docs/forensic-snapshot-local.json
.venv\Scripts\python.exe -m memebot.research.forensics --snapshot docs/forensic-snapshot-local.json --output docs/loss-statistics-local.json
```

Capture uses a PostgreSQL repeatable-read, read-only transaction and a 60-second statement timeout. It contacts no market APIs. It includes redacted configuration and private research history; raw captures/session exports are ignored by Git. Reports key portfolios by ID because names can repeat. Failed capture prints the exception class without credentials. Do not publish `.env`, endpoint URLs, raw exception traces or exported private research data.

## Safe new research run

Current settings explicitly have unlimited risk assessments and unlimited metered trades; `.env.example` now proposes 180/hour, 2,000/day and 5,000/day respectively. Apply budgets after measuring the desired control-sample/exit reserve needs; do not cut essential exit observations silently. PumpPortal's last stored status was unfunded. Fund/verify the chosen feed only through its authorized account, or use the implemented native log adapter. No provider deposits or API plan upgrades were made by this audit.

Pause entries before changing an experiment. Create a dedicated prospective portfolio/run rather than reusing the incident's 30–40% allocation. Configuration/code fingerprints are immutable experiment boundaries; new code causes a running worker to pause mismatched entries. Do not unpause an old experiment to bypass this safeguard.

```powershell
.venv\Scripts\python.exe -m memebot entries-pause
.venv\Scripts\python.exe -m memebot experiment-start --name prospective-audit-v1 --capital 100 --currency USDT
.venv\Scripts\python.exe -m memebot discover --run-seconds 30
```

`experiment-start` requires paused entries and no open positions. Check controls/risk limits before resuming. PAPER is default. Set `BULLSEYE_EXECUTION_MODE=shadow` for explicitly labelled hypothetical automatic orders, with a separate experiment portfolio. SHADOW retains the paper simulator/ledger for position evolution, emits `would_buy`/`would_sell`, and never signs/sends. Manual Telegram paper actions remain manual paper actions; do not interpret them as shadow automatic intents. There is no LIVE executor, so a claim of exact live/shadow parity would be false.

## Monitoring and outages

Every 30 seconds, `runtime_metrics` logs counters, recent p50/p90/p95/p99 latencies, primary/exit RPC request/error counts, feature-state evictions and portfolio reconciliation. Successful individual RPC timing logs are DEBUG; errors are WARNING. Metrics reset when the process restarts; historical evidence stays in PostgreSQL. Never interpret a missing percentile as zero. PumpPortal discovery timestamps are receipt estimates and excluded from actual creation-delay percentiles.

HTTP 429 opens a cooldown honoring Retry-After; authorization failures wait at least 15 minutes. Repeated transport/malformed-envelope failures open the primary circuit. One recovery probe is permitted after cooldown. New entry decisions pause when the primary circuit is open; explicit resume remains required. WSS handshake HTTP status is now stored without headers/URLs; 429 and authorization responses impose backoff. Existing WSS halt state still pauses entries. Exit refresh can use the separate fallback; missing/stale reserves cannot create a synthetic valid fill. Emergency hard stop/dump hazard/holding timeout bypass Ollama, but stale/unavailable execution evidence can still prevent an exit.

If an exit repeatedly fails, inspect durable rejected paper orders, quotes/reserves and provider state. Pending manual exits expire rather than retry forever. Fully durable bounded retries for real transaction submission/blockhash/route failures are **not implemented** because there is no live transaction path. Keep entries paused during degraded critical data and prioritize recovering position data. No stop price is a guaranteed maximum loss.

## Replay and research

```powershell
.venv\Scripts\python.exe -m memebot.research.export_session --output research_sessions/run1 --end 2026-10-01T00:00:00+00:00 --mint <MINT>
.venv\Scripts\python.exe -m memebot.research.replay --session research_sessions/run1 --configurations frozen-strategies.json --output research_sessions/run1/decisions.jsonl
.venv\Scripts\python.exe -m memebot.research.features --train-end 2026-08-24T00:00:00+00:00 --validation-end 2026-08-26T00:00:00+00:00 --output docs/features-local.json
```

Export includes prior causal history up to `--end` for selected mints, ordered by ingestion time. It saves all historical versions as `strategy_versions.json`; select the exact frozen configurations for reproduction. `--current-presets` explicitly requests a counterfactual and is not historical configuration parity. Never source-sort events or fetch current risk facts for an old decision. Compare output hashes for determinism. Replay currently evaluates decisions only and reports `pnl: null`; no fake/sample fills are substituted.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src
```

See `AUDIT.md`, `LOSS_ANALYSIS.md`, `STRATEGY_ANALYSIS.md`, `API_MATRIX.md`, and `COSTS.md` for evidence boundaries. Full live execution, complete fill replay, measured account billing and long-running survivability testing remain required before claiming production readiness.
