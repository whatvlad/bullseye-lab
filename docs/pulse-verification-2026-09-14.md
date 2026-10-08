# Verification, 2026-09-14 UTC

- 138 tests passed; Ruff and mypy passed.
- Live read-only RPC probe recovered THIEVES from completed Pump curve
  DgtDBqas667dsF5cZQ5HWHCzZCvQMQb8TYrb6t2yKS5Z to verified PumpSwap pool
  EkgDHmHiYUk6iaP53E3TPMJgjMb8QNAhdsWcLxjsPCHJ.
- After restart, automatic SELL filled at 00:39:06 UTC, position_effect=close,
  event d8a8e728-c37b-50f8-9afc-aa9148e2847f. No artificial fill or position reset.
- Portfolio accounting reconciled: cash 99.64374634 USDT, realized PNL
  -0.35625366 USDT, no remaining open positions at verification.
- Explicit configuration revision retained the portfolio and prior history.
  Controls verified: base 30%, maximum 40%, entries_paused=false.
- discover and Telegram restarted in paper mode; provider connected.
- Pulse SQL query and message rendering ran against PostgreSQL. Telegram
  registration includes /pulse. No test messages sent. No new BUY is claimed
  by this verification: entries still require the strategy and risk gates.
