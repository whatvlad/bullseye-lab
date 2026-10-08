# Production reserve normalization

Status: semantic correction implemented; runner BLOCKED. No strategy thresholds,
disagreement band, trading mode or experiment activation changed.

`market_state.normalize_trade` is the production/replay boundary. Native trade
domain events carry a frozen `NormalizedMarketState`; provider-specific reserve
fields are populated from it. The complete domain event, including original
PumpSwap PRE reserves, actual vault transfer, semantic, signature, ordinal and
slot, is persisted in `DomainEventRecord.payload`. Historical rows are not rewritten.

## Venue arithmetic

PumpSwap event physical reserves describe PRE_TRADE. For buys:

`POST token = PRE token - base_amount`

`POST quote = PRE quote + quote_amount_in_with_lp_fee`

For sells:

`POST token = PRE token + base_amount`

`POST quote = PRE quote - quote_amount_out_without_lp_fee`

These actual transfers are IDL field 12, bytes 104:112 of the event. Gross quote
amount is not a substitute. The decoder now retains that field. The normalized
semantic is RECONSTRUCTED_POST_TRADE; original values remain `raw_pre_token` and
`raw_pre_quote`. Missing transfer, impossible reserves or unknown semantics cannot
produce an observational reserve price. Price is `(POST quote + virtual offset) /
POST token`; the offset is not a physical vault transfer.

Ordinary native Pump.fun events explicitly retain POST_TRADE real and virtual
reserve fields. Multi-event transactions remain UNKNOWN in the live log-only
path. The two old cases are two observations from the same transaction at slot
452373150, signature
`5ZcMFdFPdt98Cg1hWzb9t9KDsbWdUMGKev1Tc49opLLzexJpjbMdtVvfFAmJxChtjYDfZkmuDWBvDfeWVdFAro8A`.
It has three buys for one mint. Event-to-event quote increments are 790,000,000
and 2,100,000,000; token decrements are 21,548,696,169,318 and 52,789,016,668,535.
The final physical token vault is 800,537,090,631,206 versus reported real reserve
593,637,090,631,206: inferred reserved inventory is 206,900,000,000,000. This supports
an ordered sequence, but transaction boundary balances do not independently
bootstrap the instruction-level offsets/identity. Production does not promote
these cases through an exception or infer final account state for each instruction.

## Consumer audit

| Consumer | Current source and treatment |
|---|---|
| Native provider trade fields | Production normalizer; no raw PumpSwap PRE publication |
| Rolling price, velocity, momentum and quote-reserve change | Normalized observational state; invalid prices are None |
| Strategy decision/scoring | Feature evidence; unknown/incomplete/diverged state blocks entry |
| Bonding progress/lifecycle | Explicit Pump.fun POST; no progression from invalid trade state |
| Trade storage and historical average | Normalized native price when valid; invalid event retains a historical average, never entry evidence |
| Outcome MFE/MAE | Invalid native reserve observations are skipped |
| Market-cap fee estimate | Fresh execution snapshot marginal price; fee assumptions remain estimated |
| Paper fills, realized PnL | Quantity-specific curve/pool calculation from validated RPC reserves |
| Open mark, risk/stop-loss | Existing full-position net executable sell model; stream price cannot overwrite it |
| PumpPortal vendor trade fields | UNKNOWN reserve semantics, no trusted normalized price or automatic entry |
| Research original calibration | Original PRE/POST mismatch retained as forensic evidence; not threshold eligible |

Features record state_source, state_semantics, state_quality, state_slot,
reconciled_at and continuity_status in price_evidence. Missing velocities and
acceleration remain None; an unavailable earlier velocity is no longer zero.
Paper fills record the same state evidence from the fill snapshot, avoiding
relabeling an older reference with newer RPC provenance.

`FIRST_OBSERVATION` and `EXACT` can support observational prices while state_quality
is INCOMPLETE. They do not assert coverage of direct vault transfers. HEALTHY
requires a validated RPC snapshot and complete canonical/config identity. Execution
refresh is still mandatory. Exit recovery does not require valid observational
history. A stream disconnect/unsupported mutation invalidates the shared tracker;
new ticks cannot silently clear that condition. No new per-event RPC polling exists.

## Replay

`analysis/production_state_replay.json`: 21 selected anomaly/control observations:
18 POST_TRADE, two UNKNOWN, one RECONSTRUCTED_POST_TRADE. The ~64% case remains
different valid states separated by real buys. The ~571% case now prices the large
buy's POST state at its own boundary, using the actual transfer. It no longer labels
PRE as current; the real large price movement is not erased. Original later RPC
comparisons remain SLOT_ONLY and ineligible for safety bands.

See [State validation](STATE_CONTINUITY_VALIDATION.md),
[identity limits](MARKET_IDENTITY.md) and [mutation coverage](MUTATION_COVERAGE.md).
