# Bullseye — notes for Claude

Read this first. Then `docs/STARTUP.md` (how to run) and, only as needed, the topic docs in
`docs/`. The ~90 older docs in `docs/` and `analysis/` were written by a previous agent:
treat them as **claims to verify against the code**, not as truth.

## What this is

A **PAPER-only** sniper bot for standard Pump.fun bonding-curve tokens on Solana (package
`memebot`, CLI `bullseye` / `python -m memebot`). It discovers launches from the chain,
builds rolling price/flow features, scores them with strategy presets, runs risk checks,
and simulates buys/sells against fresh RPC account state. There is no live executor.
Windows 11, Python 3.14 venv in `.venv`, PostgreSQL 17 in Docker (`compose.yaml`).

## Owner preferences (Vlad)

- Investigations first: when asked to investigate, deliver findings and a plan; **don't
  change code until he approves**. Once he says "fix it", act.
- **Never propose loosening trading thresholds** to make the bot trade.
- Don't refactor unrelated code; keep changes small; say plainly what's unverified and
  what data would settle it.
- He runs the bot himself in two console windows (see `docs/STARTUP.md`).

## Data path (live)

1. `providers/solana/pump.py` `PumpDiscoveryProvider`: Alchemy WebSocket `logsSubscribe`
   (mentions Pump program) + `accountSubscribe` on the Pump fee config. Logs only — no
   instruction data. `_handle_notification` → `_apply_notification`.
2. `providers/solana/invalidation.py` `scope_native_mutations`: rebuilds the invocation
   stack from log lines (`native_frames`) and classifies each Pump/PumpAMM/Fee frame.
   Anything unproven invalidates market state (`UNKNOWN_NATIVE_INSTRUCTION`, etc.).
3. `market_state.py` `MarketStateTracker.observe`: integer reserve continuity per market
   (FIRST_OBSERVATION / EXACT / DIVERGED / UNKNOWN / RPC_VALIDATED). Only those with an
   `observational_price` count as a confirmed price.
4. `intelligence/features/engine.py` builds windows; `strategies/price_signal.py`
   `missing_price_inputs` and `strategies/runner.py` `_decide` gate decisions.
5. `paper/engine.py` `_on_decision` → `paper/market_refresh.py`
   `CurrentPaperMarketRefresher` (atomic RPC read; entry needs `HEALTHY`) → fill simulator.
   Exits: `_evaluate_position`.
6. Side path: `providers/solana/operational_evidence.py` + `alchemy_evidence.py` stream
   full Yellowstone packets, but only for `EarlyWatch(8)` = first 8 new launches for ≤120 s,
   not for candidates.

## Fixes made on 2026-10-08 (why the bot started buying)

- Silent Pump self-CPI (Anchor emit-CPI) was classified UNKNOWN on every trade →
  `log_shape_event_cpi_frames` in `invalidation.py` accepts the strict log shape when no
  full packet exists (verified: 3,703/3,703 retained packets match byte-verified CPIs).
- Pump `BuyV3`/`SellV3`/`BuyExactQuoteInV3` (not in the pinned IDL) added to `ORDINARY`
  after checking ~400 live V3 trades chain reserves exactly.
- "Unknown" was sticky until an RPC refresh → `MarketStateTracker.observe` re-anchors a
  single Pump TradeEvent (`reason="reanchored_on_native_trade_event"`), except when the
  same transaction caused the invalidation, multi-trade txs, and PumpSwap.
  Effect: confirmed-price trades 2% → 66%, first paper buys.
- CoinGecko SOL price 429s blocked exits → `providers/price/coingecko.py` keeps last good
  price, 15 s backoff (execution still enforces ≤180 s quote age).
- RPC `-32016` (node behind stream slot) on exit refresh → short retry in
  `market_refresh.py` (0.2 s steps, 2 s budget).
- Telegram trade card on full close + 📈 chart buttons: `telegram/charts.py`,
  `storage/database/paper_history.py` (`chart`, `chart_markers`). PNG needs optional
  extra `charts` (matplotlib) — **not installed yet** (awaiting Vlad's yes); text fallback.
- Browser extension `extension/` draws paper fills on pump.fun/GMGN/Axiom/Padre/Dexscreener
  TradingView charts via `tradingViewApi.activeChart().createShape`; data from loopback
  endpoint `telegram/markers_server.py` (127.0.0.1:8765, started by the Telegram process,
  setting `chart_markers_port`). Units picked from the chart's price scale, not its label.

Known remaining issues: SLOT_REGRESSION observations (~18–27% of trades), the strategy
itself loses money so far, many decisions fail risk gates (top holder / creator holding /
buyer concentration — strategy rules, not bugs). Report:
`docs/UNKNOWN_NATIVE_INSTRUCTION_TRACE.md`.

## Commands

```powershell
.venv\Scripts\python.exe -m pytest -q          # ~586 tests, all should pass
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m ruff format --check src tests
.venv\Scripts\python.exe -m mypy src           # strict
.venv\Scripts\python.exe analysis\audit_current_no_trades.py   # funnel of current run
```

Runtime counters: each `runtime_metrics` log line has `native_instructions` (classifier
labels like `UNKNOWN_NATIVE_INSTRUCTION:<program>:<instruction>`) and `executed_evidence`.

## Gotchas

- Docker CLI path: `$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe`.
  Never `docker compose down -v`.
- One bot instance only (instance lock). Experiments are fingerprinted by **code hash**:
  after code changes a new run must start (the launcher does it), and it refuses while the
  old experiment has open positions — close them first.
- The launcher `analysis/run_operational_paper.py --continuous` is what Vlad uses; logs go
  to stderr (often redirected to `analysis/*.err.log`).
- Alchemy RPC rejects Solana **v1** transactions unless `maxSupportedTransactionVersion: 1`
  (code still passes 0 in `rpc.py`, `candidate_proof.py`; not on the live buy path).
- The on-chain Pump IDL is stale (no V3); pinned IDLs are hash-checked in `idl_schema.py`.
- `.env` holds secrets (Alchemy key, Telegram token) — never print or commit it.
- Analysis data in `analysis/` (~930 MB, one file >100 MB) is intentionally not in git.

## Git

Remote `whatvlad/bullseye-lab`. All code through the 2026-10-08 fixes is pushed to branch
`code-snapshot-20261008` (not merged to `main`). Commit/push only when Vlad asks.
