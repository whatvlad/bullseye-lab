# Infrastructure cost — 1 October 2026

The actual current monthly bill is **unknown**. Configured endpoints do not reveal paid plans, current wallet balance, billing-cycle usage or electricity/hosting costs. HTTP RPC is Alchemy, WSS is independently configured, exit RPC is public Solana, Birdeye/PumpPortal/Telegram keys are configured, and Ollama is local. Account invoices/Usage exports were unavailable. PostgreSQL uses the original local Docker volume. Redis is unnecessary.

## Cost scenarios, not invoice claims

| Setup | Services / technical purpose | Reference API cost | Traffic assumptions / limitation |
|---|---|---|---|
| Minimum research | local PostgreSQL; native RPC/WSS; cached keyless quote; optional Birdeye Standard; CLI/logs | $0 in free API subscriptions, plus local hardware/electricity | free RPC has shared limits and no continuous-trading guarantee; quotas and candidate-only risk are mandatory |
| Recommended only after measured free-tier exhaustion | one dedicated RPC/WSS provider, local DB, free optional enrichment; optional PumpPortal candidate feed | Helius Developer reference $49/month; PumpPortal variable SOL if used; no automatic purchase | advertised 10M credits / 50 RPC requests/sec; verify stream plan and actual weighted request usage; avoids redundant Alchemy+Helius paid subscriptions |
| Higher throughput only if measured latency/bandwidth warrants it | larger RPC/stream entitlement, retained event archive, optionally managed DB/host | Helius Business reference $499/month; DB/host and data bandwidth unknown | no evidence currently justifies this tier or $199/month Birdeye Premium |

PumpPortal bills 0.01 SOL per 10,000 streamed trade messages; launch/migration messages are free. A 5,000/day configured ceiling models 150,000/month → **0.15 SOL/month**, excluding duplicates or delivery after unsubscribe. Current `.env` has no trade-event cap, so 0.15 SOL is not the current bill or a guaranteed upper bound. At 50,000/day the formula is 1.5 SOL/month. USD conversion requires the actual billing-time SOL/USD value. Deposits into a provider wallet are not themselves trading PnL.

The default Local API service-fee assumption in paper execution is 0.5% per side, independent of feed cost and venue/network costs. The application does not currently call Local/Lightning transaction APIs, so these are **modeled execution costs**, not evidence of a paid executed swap.

## Request economics

Candidate risk uses up to six successful RPC calls per assessment, including batched top-holder account reads. With 2,000 assessments/day: ≤12,000 successful calls/day, ≈360,000/month, before retries and other consumers. A 180/hour cap limits candidate work to about 18 reads/minute at that six-call model. These caps now appear in `.env.example`; current settings still explicitly disable assessment quotas.

Position monitoring is a separate essential cost: five continuously open curves at a five-second interval imply approximately 2.592M reads/month. PumpSwap reserve reads can require more calls. Current inspection found zero open positions, so extrapolating that maximum as observed expenditure would be wrong. Billing CU weights differ by provider/method; request counts cannot be converted to Alchemy CU without official method weights/account Usage.

Use current RPC request counters and provider rate errors to choose a plan. Cache static mint/authority information, batch account reads, maintain rolling metrics from events and spend deep-holder requests only after the cheap funnel. Do not cache mutable liquidity/distribution past the entry freshness requirement. Circuit breakers suppress failed-primary calls while exit reads can use a separately configured fallback. Public fallback is not a production SLA and should not be used to rotate around account limits.

A metered feed needs a measured message budget and a valid funded key. Adding a paid holder or smart-wallet service before fixing execution/accounting/observation coverage has no demonstrated benefit here. No services were purchased or subscriptions changed.

References: [PumpPortal fees](https://pumpportal.fun/fees/), [Helius plans](https://www.helius.dev/pricing), [Birdeye plans](https://docs.birdeye.so/docs/pricing), [Alchemy compute units](https://www.alchemy.com/docs/reference/compute-units), [Solana public endpoint cautions](https://solana.com/docs/references/clusters).
