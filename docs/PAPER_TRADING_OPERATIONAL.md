# Operational standard Pump.fun PAPER worker

The production PAPER engine now uses current canonical atomic execution state. Live trading remains hard disabled. The existing runner thresholds, risk rules, alpha/Pulse controls and configured sizing have not been lowered to force a trade count.

The run uses the existing native discovery provider, explicitly approved by the user because configured PumpPortal events omit the identity metadata needed for cheap safe screening. This is a run-local settings selection; the global provider configuration is preserved. Telegram notifications and the allowlisted control panel are restored. Ollama is disabled by removing only its model setting; strategy and risk thresholds are unchanged.

Run from the repository after PostgreSQL is healthy:

```powershell
.venv\Scripts\python.exe analysis/run_operational_paper.py
.venv\Scripts\python.exe analysis/export_operational_paper.py
```

For a new continuous PAPER experiment, use `.venv\Scripts\python.exe analysis/run_operational_paper.py --continuous`. For a custom duration, use `--run-seconds 3600`. Start Docker Desktop/PostgreSQL first. Ollama is not required. Do not start another worker while the background worker is running.

For the current Telegram workflow, open `https://t.me/bullseye_iq_bot` and send `/start`. Existing dashboard, portfolio, strategy, chart and position controls remain available; `/pulse` opens market monitoring. Notifications come from the discovery worker, while `.venv\Scripts\bullseye.exe telegram` runs the allowlisted control panel. Both processes are currently running in the background.

Send `/history` or open **История сделок** from a refreshed `/start` dashboard. This covers all retained PAPER portfolios, including inactive runs. Each position shows coin name/symbol, full Solana mint, open/closed state, realized PnL and any remaining cost basis. Opening a coin shows its filled buy, partial sells and final sell in chronological order, along with fees and explorer/chart links. Reentries in the same mint have separate position timelines. Large lists are paginated to fit Telegram's message limits.

**Вся история (ZIP/CSV)** sends an archive directly in Telegram: `positions.csv` contains all positions and their realized PnL, and `orders.csv` contains all recorded requests, including rejected requests and their reasons. Currency and source portfolio remain explicit. Open-position realized PnL covers completed partial sales and is not a final full-position result. Unknown names remain marked unknown; full mints are still available. Future worker notifications resolve coin names from the local database asynchronously and retain full mints and Solscan/DexScreener links even if metadata lookup fails. No extra RPC enrichment is used for this presentation.

After restarting the computer, resume an active run without resetting balances or exposure:

```powershell
docker compose up -d postgres
.venv\Scripts\python.exe analysis/run_operational_paper.py --continuous --resume-existing
# Run in a second terminal:
.venv\Scripts\bullseye.exe telegram
```

Resume requires matching recorded settings/source and keeps new entries paused for operator review in Telegram. Existing exits keep running. A mismatched configuration requires an explicit recorded revision, never a silent history reset. The normal launcher creates a new experiment and refuses to replace open exposure. Pause entries in Telegram before stopping a worker with open positions.

The new-pair market-cap minimum is now unset in `config/pulse.json`, at the user's request. The final-stretch minimum remains $8,000. Captured historical experiment snapshots retain their original filters.

The script requires PAPER mode and enabled paper trading, creates a new isolated experiment using configured starting capital, records settings/source fingerprints, and observes for 900 seconds. It targets 100 completed trades but never lowers qualification to reach that target. Existing open exposure prevents starting a clean replacement experiment. Existing sizing, minimum orders, position/risk caps and strategy remain in effect.

Entries are paused at the end. An experiment with no open positions is stopped. Open positions remain durable and are reported as censored exposure; they are never invented as completed trades. If open exposure remains, resume the same captured configuration with the existing discovery worker to retain exit monitoring. A stopped process cannot actively monitor exits.

`analysis/paper_run_state.json` records the run lifecycle. Final telemetry is exported to `paper_trades.json`, `paper_candidates.json`, `paper_performance.json` and `paper_execution_assumptions.json`. Reports separate observed discovery markets, prefiltered markets, active strategy decisions and actual fills. Undefined performance statistics stay null.

Concrete operational bugs fixed in this task:

- Risk scheduling formerly required historical completeness before current canonical verification. Cheap hard exclusions now schedule bounded verification; the canonical identity guard remains mandatory before risk collection.
- Database feature hydration omitted retained price provenance. Hydration now restores it from the original domain event, preserving both standard identity and explicit incompatible-state evidence.
- The local policy output schema allowed arbitrary strings for decimal fields, producing invalid confidence such as `low`. The schema now requires numeric confidence/allocation values; policy choices still pass the existing semantic validation.
- PAPER fills formerly could use observational reserves and fixed assumed fee rates. Production fills now require atomic state and exact current fee/config inputs.
- Conservative additional slippage and adverse adjustment are explicit configuration and retained separately from verified venue fees.
- Executable MFE/MAE and peak time are retained separately from observed trade-price excursions.
- Future risk events retain the already-read canonical curve/config bank and receipt timestamp, separate from the final fill bank. This telemetry was added after the measured window; the cohort's missing pre-risk banks remain null.

Validation: 457 regression tests pass; Ruff passes; mypy checks 135 source files. The tests cover canonical bank validation, exact dynamic fees, pessimistic buy/sell outcomes, stale/missing state, failed refresh, preserved identity guard, incompatible candidate exclusions, retained database provenance and disabled live mode.

Approval review rejected a combined provider replacement/identity-guard removal because it broadened behavior and weakened a safety boundary. The implemented alternative retains the guard, verifies current identity first, and uses only the user-approved native provider selection for this bounded PAPER run. An earlier request to remove the preliminary refresh was also rejected; both preliminary and final reads remain.
