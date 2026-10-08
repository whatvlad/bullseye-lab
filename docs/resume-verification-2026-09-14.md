# Resume verification — 2026-09-14, 17:28 UTC

The previous run stopped around 00:45 UTC. No matching local bot processes
were present on resume, Docker engine was stopped and PostgreSQL refused
connections. Previous Telegram logs contained repeated getUpdates conflicts.

Started Docker Desktop and the existing PostgreSQL service without resetting
data. Added separate OS file locks for discover and Telegram in this checkout.
The application entry points acquire locks before creating external clients.
Duplicate CLI start was rejected with `telegram is already running in this project`.
Tests cover independent roles, duplicate rejection and release after abrupt exit.
This is a checkout-local guard, not a distributed Telegram ownership lock.

140 tests passed; Ruff and mypy passed. Registered an explicit code revision,
retaining the active experiment and its history. Restarted both processes in
paper mode. Provider connected, Telegram polling started. No fresh errors in
the checked startup logs. Restored one previously recovered PumpSwap pool.
Verified entries_paused=false and sizing controls 30% / 40%.

Pulse SQL and rendering work. At 17:28 UTC no candidate passed: most of the
bounded 300-token sample had stale or incomplete market data. This is not
evidence of a new profitable strategy or a successful new BUY. Historical
decisions also show holder concentration, insufficient buyer flow and RPC
holder-data gaps. Trading gates were not weakened.
