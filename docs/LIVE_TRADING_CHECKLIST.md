# Live trading readiness — BLOCKED

This repository currently has no signer, transaction constructor/submission, live balance reconciliation or LIVE mode. Settings reject `execution_mode=live`. Passing paper tests or observing profitable chart returns does not authorize or validate real trading. No funds were moved by this audit.

- [x] Existing repository audited before strategy changes.
- [x] Emergency exits cannot be bypassed by model hold/timeout.
- [x] Full-close quantity and position-side invariants enforced atomically.
- [x] Unknown source timestamp distinguished from zero latency.
- [x] Primary RPC cooldown, fallback reads, status/latency telemetry and regression coverage.
- [x] Durable paper evidence and causal deterministic decision replay.
- [ ] Demonstrated positive prospective/out-of-sample **net** expectancy and acceptable tail loss/drawdown.
- [ ] Complete executable MAE/MFE and unbiased candidate/control outcome coverage.
- [ ] Full replay of the same execution engine, reserve refresh schedule, fees, quote expiry, failed attempts and partial exits.
- [ ] Independently funded/configured profile paper portfolios and sustained paper/shadow soak tests.
- [ ] Bounded durable live sell retry state machine, signature idempotency, ambiguous-confirmation reconciliation and restart recovery.
- [ ] Token/program/network validation including mainnet genesis checks and unsupported token-extension rejection.
- [ ] Isolated signer/private-key handling, transaction simulation, actual balance-delta fills and both-side fee accounting.
- [ ] Timestamp-correct SOL and USD ledger reconciled to on-chain wallet changes; no chart-price realized PnL.
- [ ] Tested expired blockhash, simulation failure, vanished route, slippage failure, insufficient priority fee, pool collapse and provider outage.
- [ ] Portfolio failure-rate/drawdown circuit breakers using executable equity and explicit safe recovery policy.
- [ ] Measured provider request/CU/message budgets, funded stream, account entitlement and independent exit capacity.
- [ ] Explicit two-part live opt-in and startup guard; no automatic activation after paper/shadow operation.

Until these are verified, use PAPER/SHADOW only. The audit does not certify profitability or production live readiness.
