# Data sources and access

Research date: 2026-08-22. Only official documentation and official repositories
were used for decisions in this document. Provider products, fees, limits, and
program layouts change; adapters must record effective dates and re-verify their
capabilities at runtime.

## Summary

| Source | Planned role | Credential | Cost/access conclusion |
| --- | --- | --- | --- |
| Solana JSON-RPC/WebSocket | canonical on-chain accounts, logs, transactions | provider endpoint/key for production | public endpoints are free and rate-limited; official docs say they are not for production |
| Pump and PumpSwap programs | creation, curve state, completion, migration, pool state, fees | none beyond RPC | on-chain/open documentation; RPC capacity is the cost constraint |
| PumpPortal Data API | budgeted new-token, migration, and candidate-only trade stream | PumpPortal API key | discovery/migration are free; trades are capped locally because they are metered |
| Birdeye Data Services | early listings, meme lifecycle, transactions, market data, wallet/holder enrichment | Birdeye API key | free REST is limited; relevant enrichment and real-time streams require paid access as detailed below |
| CoinGecko keyless public API | SOL/USD and USDT/USD paper-accounting reference | none | keyless `/simple/price` is documented for public use; cached and freshness-checked |
| Axiom | reference UI only | none | no supported developer API verified; no integration will be implemented |
| Telegram Bot API | control plane in Phase 6 | bot token + allowed user IDs | official bot platform is free |
| X API | optional collection in Phase 10 | bearer/OAuth credentials + prepaid credits | official API is pay-per-use |
| Ollama | optional local narrative analysis in Phase 11 | local endpoint, normally no API key | local compute/storage cost; model is configurable |

No source may be replaced by invented values. Source, observation time, receive
time, availability, and confidence accompany normalized datapoints.

## Solana RPC

Official cluster documentation lists public mainnet, devnet, and testnet RPC
endpoints. It explicitly states that public endpoints are rate-limited and not
intended for production applications. At the review date, the documented public
mainnet limits include 100 requests per 10 seconds per IP, 40 per 10 seconds for
a single RPC method, and 40 concurrent connections; the page warns limits can
change.

Sources:

- [Clusters and public RPC endpoints](https://solana.com/docs/references/clusters)
- [Solana RPC infrastructure](https://solana.com/rpc)
- [JSON-RPC methods](https://solana.com/docs/rpc)
- [WebSocket methods](https://solana.com/docs/rpc/websocket)

Decision: the public mainnet endpoint is a zero-credential bootstrap default, not
a forward-paper production dependency. Phase 1 accepts configurable HTTP and
WebSocket URLs and remains vendor-neutral. A private Helius, QuickNode, Triton,
or another standards-compatible endpoint is optional; its current pricing must
be evaluated when one is selected.

Required for robust Phase 1 operation: a dedicated mainnet HTTP/WebSocket RPC
endpoint with sufficient log subscriptions, request capacity, history, and an
explicit service limit/SLA. No transaction-send permission is needed.

## Pump and PumpSwap

Pump's official repository documents the Pump bonding-curve program and current
IDL. The Pump program is deployed at
`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`; a completed curve has
`complete == true` and `real_token_reserves == 0`, and the permissionless,
idempotent `migrate` instruction moves it to PumpSwap.

PumpSwap is the constant-product AMM at
`pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`. Canonical migrated pools use
index `0`. Current pool state includes a signed `virtual_quote_reserves` field;
official documentation says effective quote reserves must include it even though
it is currently zero. This is an example of why old copied pool math is unsafe.

Official sources:

- [Pump program and bonding-curve state](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md)
- [Pump IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json)
- [PumpSwap program and pool state](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_SWAP_README.md)
- [PumpSwap IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_amm.json)
- [Current lifecycle explanation](https://pump.fun/docs/bonding-curve)
- [Current fee schedule](https://pump.fun/docs/fees)

The current public fee page describes a 1.25% bonding-curve total fee and a
dynamic canonical PumpSwap schedule, including distinct SOL- and USDC-quoted
markets. Those values are documentation evidence, not constants to embed in
paper execution. Phase 5 records configurable conservative assumptions and labels
fills high-confidence rather than falsely exact while dynamic configuration is
not fully captured.

## CoinGecko quote reference

Phase 5 uses the documented keyless public root and `/simple/price` for `solana`
and `tether` against USD. A USDT portfolio derives SOL/USDT as SOL/USD divided by
USDT/USD; it never silently relabels USD. Provider timestamps are mandatory and
stale observations reject paper execution.

Source: [CoinGecko Keyless Public API](https://docs.coingecko.com/docs/keyless-public-api)

Access: no Pump API key is needed for direct read-only on-chain observation. Phase 1 is
pinned to official repository commit
`9c82f61cb711b044a17f770ab8ce9f9bdf78f333`. The raw IDL SHA-256 values are
`b90bc471327f671449271d5d1d42354d1fae6f5a06502f5834459a3108138e49`
(`pump.json`) and
`6b5c7ec4e5ef9742fa99dc57b0d75b1031b379bba02a7e1b3c5a4cad68d77e56`
(`pump_amm.json`). The runtime decodes only the explicitly tested Phase 1 event
and account subset and uses no unofficial trade API.

## PumpPortal budgeted stream

When `BULLSEYE_PUMPPORTAL_API_KEY` is configured, Bullseye stops using the
high-volume global Helius/Solana `logsSubscribe` stream. It opens one PumpPortal
WebSocket, receives new-token and migration events for free, and creates
short-lived paid trade subscriptions only for a bounded number of newly observed
tokens. Candidate data remains `INSUFFICIENT_DATA` until independent RPC risk and
market validation succeeds.

The provider supports a short observation window and a hard paid-message cap. To
avoid consuming the entire allowance in minutes, candidate subscriptions are
rate-spaced (30 minutes by default) and end after 25 trade events even if the time
window remains open. The daily counter is restored from persisted events after a
restart, so restarting the worker cannot bypass the cap. When exhausted, free
launch/migration discovery remains active and only token trades become unavailable.

The local `.env` currently caps the research run at 1,000 paid trade messages per
UTC day. Provider rounding or policy changes can differ, so the PumpPortal
dashboard remains authoritative.

Sources:

- [PumpPortal real-time data](https://pumpportal.fun/data-api/real-time/)
- [PumpPortal fees](https://pumpportal.fun/fees/)

## Birdeye Data Services

Official documentation confirms the following relevant surface:

- `SUBSCRIBE_TOKEN_NEW_LISTING`, including `pump_dot_fun` and `pump_amm` sources;
- `SUBSCRIBE_MEME`, with source, curve progress, creation, and graduation filters;
- token/pair transactions, prices/OHLCV, stats, new pairs, and large trades;
- wallet transaction streams;
- REST token overview, creation info, security, holder, and holder distribution.

Sources:

- [New token listing WebSocket](https://docs.birdeye.so/reference/new-token-listing)
- [Meme lifecycle WebSocket](https://docs.birdeye.so/reference/meme-stats)
- [WebSocket overview and reconnect guidance](https://docs.birdeye.so/docs/websocket)
- [Token/pair transaction stream](https://docs.birdeye.so/reference/tokenpair-transactions)
- [Token security](https://docs.birdeye.so/reference/get-defi-token_security)
- [Solana holder distribution](https://docs.birdeye.so/reference/get-holder-v1-distribution)
- [Token creation info](https://docs.birdeye.so/reference/get-defi-token_creation_info)
- [Package accessibility matrix](https://docs.birdeye.so/docs/data-accessibility-by-packages)
- [Pricing](https://docs.birdeye.so/docs/pricing)

### Access-tier findings

As documented on the research date:

- Standard is $0 with 30,000 compute units, limited endpoints, and a 1 rps
  account rate limit.
- Lite starts at $39/month and Starter at $99/month; the package matrix lists
  token security, creation info, and Solana holder distribution on paid tiers,
  not Standard.
- Premium is listed at $199/month and Business at $499/month on the pricing page.
- The pricing page says Premium includes WebSockets and 500 connections, while
  the WebSocket overview says access is available for Business subscribers and
  describes 500 connections there. The package matrix also requires careful
  column interpretation.

Because the official pages disagree, the code does not decide entitlement from
a configured plan name. The Phase 6 Birdeye adapter probes requested REST
capabilities and reports confirmed/unavailable results. Before a future WebSocket
purchase, confirm the exact real-time methods and limits in the dashboard/support.

Birdeye's documented `token exit liquidity` V3 endpoint is Base-only, not Solana.
It must not be called for a Solana token. Solana exit-liquidity estimates will be
derived from verified on-chain curve/pool state or remain unknown.

The current Standard key is used for low-frequency REST enrichment only. It does
not permit the Birdeye listing/meme WebSockets, so Helius is the canonical real-time
discovery source.

## Axiom

Official Axiom documentation was searched for developer, API, authentication,
WebSocket, and API-key material. The published documentation describes the user
trading interface, wallet tracking, Twitter monitor, fees, and UI workflows, but
no supported developer API, public schema, authentication flow, or API terms were
verified.

Sources reviewed:

- [Axiom official documentation](https://docs.axiom.trade/)
- [Axiom market UI](https://docs.axiom.trade/axiom/swap/market)
- [Axiom documentation FAQ](https://docs.axiom.trade/faqs)

Conclusion: Axiom is a product/reference interface only. Bullseye will not invent
endpoints, inspect private traffic, automate its UI for critical operation, or
request Axiom credentials. An adapter may be proposed only after an official
developer interface is published and re-verified.

## Birdeye Standard account verified in Phase 6

The supplied key authenticated successfully on 2026-08-22. The official credits
endpoint reported 30,000 remaining CU before integration probes. Successful probes
confirmed credits, supported networks, token price, token market data, and new
listing REST access. The official pricing table gives Standard 30,000 CU, limited
data, and 1 rps; the package-access table does not include WebSockets for Standard.

Bullseye therefore uses:

- Helius HTTP/WebSocket RPC for continuous Pump/PumpSwap on-chain discovery;
- Birdeye REST only for low-frequency capability checks and cached market enrichment;
- a 1.1-second minimum request interval;
- a configured 25,000 CU planning guardrail, leaving an operational buffer; this is
  informational rather than a local hard quota, so Birdeye's credits endpoint remains
  the source of truth;
- five-minute per-token market-data caching.

The new-listing endpoint costs 30 CU per call. Polling it once per minute would cost
about 1.3 million CU in a 30-day month, so it is deliberately not used as a Standard
plan background scanner. Price costs 3 CU, market data 10 CU, and new listings 30 CU
according to the current official CU table. Costs may change and must be rechecked.

Sources:

- [Birdeye pricing](https://docs.birdeye.so/docs/pricing)
- [Data accessibility by package](https://docs.birdeye.so/docs/data-accessibility-by-packages)
- [Compute Unit cost](https://docs.birdeye.so/docs/compute-unit-cost)
- [Authentication](https://docs.birdeye.so/reference/birdeye-api-authentication)
- [Credits usage](https://docs.birdeye.so/reference/get-utils-v1-credits)

## Telegram

Telegram's official Bot Platform documentation says it is free for users and
developers. Phase 6 uses a BotFather token and an explicit allowlist of Telegram
numeric user IDs. The token remains environment-only.

Sources:

- [Bots: introduction for developers](https://core.telegram.org/bots)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## X

The official X API pricing page currently documents prepaid, pay-per-use credits
with per-resource read pricing and spending limits. Collection is therefore an
optional paid data source, not a requirement for on-chain operation. Phase 10
will use supported APIs only, cache/deduplicate responsibly, and default social
trading weight to disabled.

Source: [X API pay-per-use pricing](https://docs.x.com/x-api/getting-started/pricing)

Required later: an X developer app and bearer/OAuth credentials with credits.
No browser scraping is an accepted fallback.

## Local services

PostgreSQL is open-source and needs no third-party API key. The Compose bootstrap
uses a local development password that must be replaced for any non-local
deployment. Redis is deferred. Ollama is an optional local endpoint and no model
is selected until installed VRAM, model size, quantization, context, and latency
are measured.

## Credentials checklist

Phase 0–1 tests and local diagnostics: none.

Phase 1 recommended:

1. Dedicated Solana mainnet HTTP and WebSocket RPC URLs.
2. Birdeye API key. The supplied Standard account is REST-only; Premium or higher
   is required before Birdeye WebSockets can be enabled.

Later phases:

3. Telegram BotFather token and allowed numeric user IDs (Phase 6).
4. X API credentials and prepaid credit budget (Phase 10, optional).
5. Ollama endpoint/model name (Phase 11, optional).

No Solana private key, seed phrase, signer, or funded wallet is required or
accepted during the paper-trading phases.
