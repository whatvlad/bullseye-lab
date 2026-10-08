# Phase 1 discovery operations

Status: implemented  
Network: Solana mainnet  
Execution: read-only paper research; no signer exists

## Data flow

```text
Helius or standard Solana WSS
  -> logsSubscribe(Pump) + logsSubscribe(PumpSwap)
  -> invocation-aware Anchor event decoder
  -> deterministic domain events
  -> on-chain account validation over HTTP RPC
  -> idempotent PostgreSQL token registry
```

The provider observes token creation, Pump trades, curve completion, Pump-to-
PumpSwap migration, and direct PumpSwap pool creation. A token progresses through
`bonding_curve`, `final_stretch`, `graduation`, and `post_graduation` when the
corresponding evidence arrives.

`final_stretch` starts at 80% by default. For launches observed from creation,
progress is the fraction of initial real curve inventory sold. Change the
research hypothesis with `BULLSEYE_PUMP_FINAL_STRETCH_PERCENT`; it is not a trade
threshold.

## Configuration

Copy the complete provider URLs into `.env`:

```dotenv
BULLSEYE_SOLANA_RPC_HTTP_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
BULLSEYE_SOLANA_RPC_WS_URL=wss://mainnet.helius-rpc.com/?api-key=YOUR_KEY
BULLSEYE_SOLANA_EXIT_RPC_HTTP_URL=https://api.mainnet-beta.solana.com
BULLSEYE_SOLANA_COMMITMENT=confirmed
```

Do not add a separate Helius key variable. Do not paste real URLs into logs,
issues, or screenshots because they contain the credential.

Optional transport/retry values are documented in `.env.example`. The safe
configuration report prints only the RPC hostname.

## Commands

```powershell
docker compose up -d postgres
bullseye db-upgrade
bullseye rpc-check
bullseye discover
```

The discovery command runs until `Ctrl+C`. Use
`bullseye discover --run-seconds 30` for a bounded connectivity test.

Query persisted state:

```powershell
bullseye provider-health
bullseye token <mint>
```

## Validation states

- `discovered`: an identity event exists but no market evidence is projected yet.
- `verified_market_data`: evidence came from a pinned canonical Pump/PumpSwap
  program event, or the required curve/pool account identities were refreshed.
- `insufficient_data`: referenced accounts were unavailable or the pool had no
  usable liquidity; missing data is not replaced with zero.
- `rejected`: on-chain ownership, schema, identity, or canonical migration checks
  failed.

Validation describes data reliability, not investment safety. Token-risk checks
belong to Phase 3.

## Reconnect and duplicate behavior

Both subscriptions are recreated after any connection failure. Delay grows
exponentially, is capped, and includes jitter. Health transitions and reconnect
counts are stored in `provider_health`.

Three consecutive WebSocket `InvalidStatus` responses open a circuit breaker.
New paper entries are paused, identical health events are deduplicated, and the
provider probes only every 15 minutes until service returns. Resume entries from
Telegram only after the RPC quota or credentials have been restored.

Normalized source IDs use the Solana signature, log ordinal, and event kind.
`domain_events.event_id` is the final idempotency guard, while
`tokens(network, mint)` independently prevents duplicate token identities.

## Known boundary

Bonding progress is calculated from the authoritative initial reserve captured at
creation. Phase 2 restores active curve baselines and validated PumpSwap pool
identities from PostgreSQL after a worker restart; it never guesses an absent
historical reserve.

Birdeye is not active without a supplied key and confirmed subscription access.
The on-chain path continues independently.
