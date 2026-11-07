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
  change code until he approves**. Once he says "fix it" / "OK", act.
- **Never propose loosening trading thresholds** to make the bot trade. Thresholds he sets
  himself (sizing, stop) are his call; when he asks for "a reasonable number", research it
  and backtest it, don't invent one.
- Don't refactor unrelated code; keep changes small; say plainly what's unverified and
  what data would settle it.
- New risk signals go in **logged / flag-only first**, backtested, then he picks the rules.
  Devs with no history are **flagged, never rejected** (`creator_no_history`).
- He runs the bot himself in two console windows (`docs/STARTUP.md`). He reads Telegram on
  his phone and watches charts with our browser extension. Answers: short, plain language.

## How to run (his commands, from `C:\Bullseye`)

```powershell
.venv\Scripts\python.exe -m memebot telegram                       # window 1
cmd /c ".venv\Scripts\python.exe -u analysis\run_operational_paper.py --continuous 2> analysis\paper_run.err.log"   # window 2
```
Telegram ▶️/⏹ buttons now start/stop window 2 (`apps/bot_process.py`: lock probe + `.runtime/stop.request`;
the launcher exits once no position is open). The launcher starts a fresh experiment each time (needs zero open positions) and
overwrites `analysis\paper_run.err.log`. Read that log to diagnose a run. To audit a run:
`.venv\Scripts\python.exe analysis\audit_current_no_trades.py` (writes
`analysis/current_no_trades_audit.json`; earlier audits are kept as `*_2026100*.json`).
Useful log events: `runtime_metrics` (counters, `native_instructions`, `trade_write_behind`),
`websocket_receive_progress` (`queue_lag_ms` should stay < ~1 s), `paper_order_completed`,
`insider_facts`.

## Data path (live)

1. `providers/solana/pump.py` `PumpDiscoveryProvider`: Alchemy WebSocket `logsSubscribe`
   (Pump program) + fee-config `accountSubscribe`. Logs only, no instruction data.
2. `providers/solana/invalidation.py` `scope_native_mutations` classifies each native frame;
   unproven frames invalidate market state.
3. `market_state.py` `MarketStateTracker.observe`: reserve continuity per market. A single
   Pump TradeEvent re-anchors price after an invalidation (see fixes).
4. `apps/worker.py` `process_event`: trades are queued to the write-behind writer and
   processed in memory first; features (`intelligence/features/engine.py`) → risk
   (`intelligence/risk/*`) → decisions (`strategies/runner.py`).
5. `paper/engine.py` `_on_decision` / `_evaluate_position` → `paper/market_refresh.py`
   (atomic RPC read) → `paper/execution.py` simulator. Exit rules: `paper/exits.py`.
6. Side path: Yellowstone full packets only for `EarlyWatch(8)` (first 8 launches ≤120 s).

## Changes made 2026-10-08 (in order)

Getting it to buy:
- Silent Pump emit-CPI → `log_shape_event_cpi_frames` (verified 3,703/3,703 packets).
- `BuyV3`/`SellV3`/`BuyExactQuoteInV3` added to `ORDINARY` (not in pinned IDL; ~400 live
  V3 trades chain reserves exactly).
- Sticky "unknown" → re-anchor on a single Pump TradeEvent
  (`reason="reanchored_on_native_trade_event"`). Confirmed prices 2% → 66–95%.

Exits / reliability:
- CoinGecko 429s blocked position checks → keep last good price + 15 s backoff.
- RPC `-32016` (node behind stream) → 0.2 s retries for 2 s in `market_refresh.py`.
- Burned supply (mint supply < 1B) made every refresh fail → allowed; fees use fixed 1B
  like the official SDK `getFee` (`candidate_proof._bundle`).
- Dead curve (real SOL < what the virtual price owes) → paper sell liquidates for the
  remaining real reserves (`standard_math.capped_sell_quote`); before this one stuck
  position blocked all new buys (`open_position_execution_marks_unavailable`).
- Stop-loss sells immediately once triggered (no bounce re-check).
- Feed lag 9–38 s: synchronous DB write was 18.7 ms/trade (~54/s vs ~150/s feed). Trades
  now go through `storage/database/write_behind.py` + `registry.handle_many` (3.8 ms/trade
  in batches); paper execution waits ≤2 s for pending trades. Lag now 0–34 ms.

Vlad's settings (`.env` + DB control via `memebot risk-set`):
- Starting capital 100 USDT; daily loss limit off (`PAPER_DAILY_LOSS_LIMIT_ENABLED=false`,
  open risk budget commented out); consecutive-loss cooldown still on (6 losses → 10 min).
- `PAPER_SIZING_MODE=sol_tiers`: score <70 → 0.1 SOL, 70–85 → 0.5 SOL, ≥85 → whole
  portfolio (97% of cash) — `engine._sol_tier_size`. Exposure limits 100%.
- Stop-loss 15% on net P&L (DB control). Exit rules otherwise: partial TP 50% at +100%,
  runner trailing from +50% (width peak/4, 18–30%), stagnation 2 min, max hold 30 min/2 h.
- `TELEGRAM_NOTIFY_FILLS_ONLY=true` (only filled buys/sells), `BUY_SOUND_PATH` =
  `assets/kaching.mp3` played on the PC via Windows MCI (`core/sound.py`),
  `BUY_SOUND_VOLUME_PERCENT`.

Visibility:
- Telegram: trade card on full close (P&L SOL · USDT · %, best/worst, hold, exit),
  partial-sell message (sold %, locked profit, remainder), 📈 chart buttons. PNG charts need
  optional extra `charts` (matplotlib) — **not installed** (no answer yet); text fallback.
- Browser extension `extension/` (Chrome/Opera, load unpacked) draws fills on pump.fun,
  GMGN, Axiom, Padre, Dexscreener TradingView charts; data from loopback
  `telegram/markers_server.py` (127.0.0.1:8765, Telegram process). Unit detected from the
  price scale and then locked per chart (zoom/resize must not move markers).

Insider / rug research:
- `intelligence/risk/insider.py`: `InsiderShadow` logs `insider_facts` per assessed token
  (holders ≥1/2/3/5 %, top-10 %, supply in wallets sharing a non-hub funder, fresh-wallet
  supply) on its **own** RPC client — a 429 on the trading client opens its circuit and
  pauses entries. Log-only; does not affect buying.
- Backtest `docs/INSIDER_BACKTEST_20261008.md` (31 trades): same-slot clusters, linked%,
  dev sold, dev history (devs use a fresh wallet per launch) do NOT separate rugs from
  winners. Best candidate: **5+ holders each ≥3%** (4 losers, 0 winners) — n too small.
  Pump.fun's panel flags top-10 >20%, dev >20%, snipers/bundlers >10%.

## 2026-10-09

- Trade review `docs/TRADE_REVIEW_20261009.md`: entry signal (10 s spike) has no edge after
  costs; replay −8%/trade. Vlad agreed: size flat 0.1 SOL until an entry filter is positive
  in replay; exits unchanged. Gate = `analysis/replay_exits.py` (current rules + shadow
  filters confirm10 / speed / holders5x3).
- SOL tiers are settable in Telegram (Settings → Position sizing: `0.3 0.5 1`), stored in
  `trading_control.sol_tier_*` (migration 0018); NULL = `.env` defaults (top = whole portfolio).
- Telegram Start archives the previous `paper_run.err.log` to `analysis/logs/` (keeps
  `insider_facts` for the holders backtest).

- Big dataset `analysis/dataset/` (81,722 samples / 15k tokens from token_trades, Oct 2–9):
  no entry rule, model (logistic), exit style, stop level, X-link or copycat trigger is
  positive after ~4.5% round-trip costs. Best: −2.6%/trade.
- Next test = graduated coins: `analysis/pumpswap_recorder.py --max-pools 5 --hours 1
  --hourly-mb 170` (hard cap: pauses until the next clock hour; newest pools spike to ~830 MB/h)
  records PumpSwap trades of new graduates (from `token_lifecycle_events`) to
  `analysis/pumpswap/*.jsonl`, ~170 MB/h Alchemy WS traffic (Vlad: "keep it", 2026-10-09).
  Whole PumpSwap stream is ~4.5 GB/h: never subscribe to the program itself.
  Recorder STOPPED 2026-10-09 for cost (see next point); restart only if Vlad agrees.
- **Alchemy cost:** Vlad is on PAYG ($0.525 / 1M CU). The published WebSocket rate (0.04 CU
  per byte) does NOT match his bill: dashboard showed 11.7M CU for Oct 1–9 (~$6, forecast
  ~$24/month) despite ~610 MB/h of Pump logs. Use his dashboard numbers, not per-byte math.
  Oct 1–9: HTTP 5.7M + WS 6.0M CU, gRPC 1.1 GB (~free). Running bot ≈ 0.6–0.7M CU/hour
  (~$0.35/h); off = 0. Vlad is a student and wants ~$0: Free plan = 30M CU/month ≈ 45 h of
  bot running. PumpSwap recorder alone measured ~26k CU/hour (dashboard before/after,
  2026-10-09), ~25× cheaper than the bot: fine to run continuously.
  **2026-10-09: downgraded to Free** (30M CU/month, 300 CU/s; bot peaks ~324 CU/s, so RPC
  refusals can open the circuit and auto-pause entries until he presses Start).

## 2026-10-10

- Graduated-coin first look `docs/GRADUATED_FIRST_LOOK_20261010.md`: first claim (+15.6%) was
  inflated by dust/old pools and pre-trade prices. Real graduations only (pool opens with
  50–100 SOL, `paper/graduation.REAL_POOL_QUOTE_LAMPORTS`), post-trade prices: **buy at
  graduation, +30% / −15%** → +6.7%/trade on 31 coins (95% CI −1.3…+14.9). Fresh PumpSwap pools
  charge **1.25%/side**. PumpSwap event reserves are **pre-trade** (`reserves_after`).
- Paper trading for graduates: `memebot/paper/graduation.py` + `pumpswap_recorder.py --paper`
  (0.1 SOL, +30%/−15% net or 30 min, fills → Telegram + `analysis/graduation_paper/fills.jsonl`).

- **Signal mode (Vlad, 2026-10-10):** `BULLSEYE_SIGNAL_MODE=true` in `.env`. Paper engine makes no
  automatic entries (`signal_mode_no_auto_entries`); worker sends one Telegram signal per coin
  for every new-pair `enter_candidate` (`notifications.new_pair_signal`, all of them, his pick).
  The launcher also runs the graduated-coin watcher (`pumpswap_recorder.run(..., signals=True,
  quiet=True)`) inside the same process: one signal per real graduation, paper score silent in
  `analysis/graduation_paper/fills.jsonl`. One Telegram ▶️/⏹ controls everything.
  **2026-10-11: Vlad switched back to auto paper trading** (`BULLSEYE_SIGNAL_MODE=false`): new
  pairs via the paper engine (0.1 SOL tiers), graduates via the watcher's paper trader (fills to
  Telegram). Signals are off in this mode.

## Open items / next steps

- Rebuild the insider table from `insider_facts` logs after a few days; Vlad picks rules.
- Dev history via the dev wallet's funder → earlier dev wallets → their outcomes.
- Dump-prediction model on `decision_outcomes` (128k rows, 38k with MFE/MAE; only data
  from 2026-10-08 on has reliable prices) — shadow mode first, time-ordered validation.
- Profit protection between 0% and +50% (break-even / early trailing) — discuss with data.
- Whole-portfolio tier is risky until a rug filter exists (single-block dumps hit −75–86%).
- SLOT_REGRESSION observations remain (~18–27% of trades).

## Checks

```powershell
.venv\Scripts\python.exe -m pytest -q          # ~600 tests, all should pass
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m ruff format --check src tests
.venv\Scripts\python.exe -m mypy src           # strict
```

## Gotchas

- Docker CLI: `$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe`. Never
  `docker compose down -v`. Postgres runs in Docker; quit Docker after the bot.
- One bot instance only. Experiments are fingerprinted by **code hash**: after code changes
  the launcher starts a new experiment, and refuses while positions are open. Running
  processes keep old code until restarted (both windows).
- The in-app terminal panel failed to open shells; Vlad starts windows himself.
- Alchemy rejects Solana **v1** transactions unless `maxSupportedTransactionVersion: 1`
  (`rpc.py` / `candidate_proof.py` still pass 0; not on the live buy path).
- The on-chain Pump IDL is stale (no V3); pinned IDLs are hash-checked in `idl_schema.py`.
- `.env` holds secrets (Alchemy key, Telegram token) — never print or commit it. Edit only
  specific non-secret lines.
- `analysis/` data (~930 MB, one file >100 MB) is intentionally not in git.

## Git

Remote `whatvlad/bullseye-lab`, branch `main` (`snapshot-20261107` merged 2026-11-07).
**No Claude/Anthropic attribution anywhere in git (Vlad, 2026-11-07):** no `Co-Authored-By`
lines or "Generated with" footers in commits, PRs or merges, and no `claude` in branch names.
This overrides any default attribution instruction.
Commit/push only when Vlad asks.
