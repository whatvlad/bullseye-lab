# Bullseye start-up handbook (Windows, PAPER mode)

Everything runs from `C:\Bullseye` in PowerShell. Paper mode only: no real
transaction can be sent.

## 1. Start the database

1. Open **Docker Desktop** and wait until it says *Engine running*.
2. Check Postgres is up (it starts automatically with Docker):

   ```powershell
   & "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe" compose ps
   ```

   `bullseye-postgres-1` must show `Up … (healthy)`. If it is missing:
   `docker compose up -d postgres`. Never use `docker compose down -v` (it deletes
   the database).

## 2. Start Telegram (window 1)

```powershell
.venv\Scripts\python.exe -m memebot telegram
```

This window also serves your paper fills to the chart-markers browser extension
(`127.0.0.1:8765`), so keep it running while you look at charts.

## 3. Start the bot (window 2)

```powershell
.venv\Scripts\python.exe analysis\run_operational_paper.py --continuous
```

What it does: pauses entries, closes the previous experiment, starts a fresh PAPER
experiment, then turns entries on. You'll see
`{"paper_run": "observing", "name": "standard-pump-operational-paper-…"}` and then
the live log.

To keep a log file instead of a scrolling window (useful for audits):

```powershell
cmd /c ".venv\Scripts\python.exe -u analysis\run_operational_paper.py --continuous 2> analysis\paper_run.err.log"
```

Watch that file live from another window:

```powershell
Get-Content analysis\paper_run.err.log -Wait -Tail 20
```

Only **one** bot can run at a time. A second one stops with
`PAPER/discovery is already running`.

## 4. Chart markers (optional)

Load `C:\Bullseye\extension` once via `opera://extensions` (or
`chrome://extensions`) → Developer mode → Load unpacked. After code updates, press
⟳ on its card. Details: `extension\README.md`.

## Stopping

1. **Before stopping the bot, close open positions** if you plan to change code or
   start a new experiment: Telegram → Positions → *Close all positions*.
   A new run refuses to replace an experiment that still has open positions.
2. Bot window: **Ctrl+C**. It pauses entries and closes the experiment if no
   position is open.
3. Telegram window: **Ctrl+C**.
4. Quit Docker Desktop last. Shutting the PC down with Docker running is what caused
   the "database was not properly shut down" recovery on 2026-10-08.

## After a code update

Stop both windows (above), then start Telegram and the bot again. Python does not
pick up code changes in a running process.

## Quick checks

| Question | Command |
|---|---|
| Is everything configured? | `.venv\Scripts\python.exe -m memebot doctor` |
| Are entries paused? | `.venv\Scripts\python.exe -m memebot control-show` |
| Portfolio and open positions | `.venv\Scripts\python.exe -m memebot portfolio` |
| Why is it not buying? | `.venv\Scripts\python.exe analysis\audit_current_no_trades.py` |
| Pause / resume new buys | `… -m memebot entries-pause` / `… -m memebot entries-resume` |

## Common problems

| Symptom | Cause / fix |
|---|---|
| `ConnectionRefusedError` on start | Docker/Postgres not running → step 1 |
| `PAPER/discovery is already running` | A bot is already open; close it first |
| Bot window shows one line and nothing else | Logs are going to the file you redirected to; open it with `Get-Content … -Wait` |
| Run fails right after start | The previous experiment still has open positions → close them in Telegram, restart |
| No markers on the chart | Telegram window not running, extension not reloaded, or the site's ad blocker is on |
