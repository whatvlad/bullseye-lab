# Bounded standard Pump.fun candidate execution proof

The stream remains observational. This service proves one earned candidate and
never repairs or promotes the entire global stream. The runner stays **BLOCKED**;
no orders, trading database mutations, bands, or strategy threshold changes were made.

## Funnel

`STANDARD_DISCOVERED → OBSERVATION_ELIGIBLE → ARITHMETIC_CONTINUITY_OK →
SERIOUS_CANDIDATE → CANDIDATE_PROOF_PENDING → EXECUTION_READY`.
Any invalid/excluded stage goes to `REJECTED`. `FunnelStage`, `Candidate`, and
`observational_stage()` are in `src/memebot/paper/candidate_proof.py`.

Discovery records an explicit standard/non-Mayhem flag. Supported SOL quote and
single-event flow permit cheap observation; exact integer arithmetic permits
observational progression. Known divergence, migration, completion, Mayhem,
PumpSwap, unsupported quotes or ambiguous multi-event transactions never trigger
candidate proof. Arithmetic EXACT does **not** authorize execution.

The passive producer reuses the existing aggressive preset's score, completeness,
age, trade count, distinct buyers, observation span, flow, attribution, concentration,
price-change and regime constraints. No parameter was lowered to obtain a sample.
Risk is explicitly unknown until separately assessed; opportunity qualification is
permission to spend proof reads, not permission to trade. All amounts used in this
capture are research quantities, not strategy position-sizing changes.

## Proof package and synchronization

1. Read a bounded recent signature window for the canonical curve.
2. Read one `getMultipleAccounts` batch containing mint, curve, both locally derived
   token-program vault possibilities, Pump Global, Pump FeeConfig and the mint's
   sharing-config PDA. Exactly one returned bank context binds identity, reserve
   and config slots. Canonical PDA/address, ownership, initialized supply, vault
   mint/authority, quote, mode, completion and token-extension checks must pass.
3. Read the selected vault's bounded signature window. Both windows must reach
   the observed anchor. Their union must remain within the signature budget.
4. Obtain each relevant transaction in the bounded union. Each must contain one
   standard Pump trade, an ordinary supported native instruction, matching event
   CPI bytes, canonical vault metadata and exact physical quote/token changes.
   Unexplained inner/top-level mutation, truncation or multi-event flow rejects.
5. Verify reserve arithmetic across the ordered sequence, constant physical-vault
   inventory/nonreserve quote offsets, native instruction/fee parity, and terminal
   reserve equality with the atomic account snapshot. Multiple transactions in
   the same slot reject because address-history RPC does not establish their index.
6. Repeat the curve/vault history reads as a fence. Any changed history rejects.
   The native/config invalidation generation must also remain unchanged throughout
   the proof. A timeout or exhausted budget never grants approval.

A single batch establishes `ONE_RPC_BANK_CONTEXT`, **not** transaction synchronization
by itself. Execution proof additionally requires the anchored native sequence,
physical invariants, terminal-state equality and unchanged history fence. The
anchor is itself proven from native metadata; no completeness before that bounded
anchor is claimed. Direct token/quote donations or unexplained physical changes
are conservatively rejected. Transfer-fee/hook/frozen/unknown Token-2022 extensions
also reject; supported metadata/reference extensions do not change transfer math.

The package retains decoded account/config fields and versions, canonical
references, raw account batch/address mapping, recent signatures, native parity,
quantity-specific buy/sell quotes and the following timestamps:

`candidate_detected_at`, `proof_started_at`, `identity_slot`, `reserve_slot`,
`config_slot`, `proof_completed_at`, `decision_at`, `execution_refresh_at`.

`proof_latency_ms` measures active proof duration; candidate queue age is checked
separately. `decision_age_ms` is decision time minus proof completion.
`slot_span` measures identity/reserve/config account contexts (zero for the one
batch). `sequence_slot_span` separately measures the historical-anchor-to-account
span. Missing decision/refresh timestamps remain null in passive failed attempts.

## Budgets and cache

`ProofPolicy` exposes research safety caps: 12 requests per candidate including
refresh, four relevant signatures, a 12-second deadline and 2,000 ms proof/queue
freshness. These are explicit configurable research limits, not calibrated trading
thresholds or disagreement bands. There are no per-event RPC reads. The passive
producer caps a capture at 120 seconds, eight candidates and 96 shared RPC requests.

Stable cache entries include canonical mint/curve/vault, token program and decimals,
mint bytes hash, creator/override authority fields, config address binding and
config hashes. Fee schedules are decoded once per version. Local invalidation handles
completion/migration and shared config generation changes. Explicit invalidation
and version, owner, canonical or authority mismatch revoke receipts. Generation
checks prevent an invalidation racing with an in-flight proof from approving.

After PASS, `execution_refresh()` is mandatory before obtaining order-time quotes.
It performs **one fresh account batch**, checks cached bindings/current ownership,
mode/completion, config versions and inventory/quote offsets, then recomputes the
quantity quotes from current reserves. It performs no history reconstruction and
reuses decoded config versions. Stale/future timestamps and refresh failures reject
and revoke the applicable receipt. A proof PASS alone is not an order fill.

The service is a read-only proof API; it does not activate the runner or bypass its
existing experiment, risk, price, calibration or paper execution gates. The old
static-fee simulator must not be used to turn a proof packet into a fill. Any later
order-path integration must consume the refreshed, quantity-specific validated
quotes and retain their evidence.

## Validation and observed limits

Encoded canonical account/native transaction tests exercise both buy and sell PASS,
identity/config mismatch, unsupported mutation, history uncertainty, budget/deadline,
staleness, cheap refresh, cache reuse/invalidation and races. The eight old standard
divergences are separate forensic regressions; their causes remain unknown and do
not prevent building the prospective architecture. Known divergence and unexplained
physical mutations cannot approve prospective execution.

Two bounded passive captures exercised nine serious candidates. There were **zero
live PASS**. Five rejected unvalidated ordinary cashback/reward/shared-fee routing;
four rejected missing bounded anchors. In the retained detailed failure, the
signature index was behind the observed anchor slot, so coherent account reads and
research quotes could not establish a native sequence. No extra polling or widened
window was used to manufacture a pass. See `analysis/candidate_execution_proofs.json`.
