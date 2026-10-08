# Standard Pump.fun runner prerequisite

The trading universe is `STANDARD_PUMP_FUN_ONLY`. `runner-edge-prospective-v1`
remains **BLOCKED**. No worker, experiment or live execution was started. Strategy
thresholds and disagreement bands were not changed.

## Eligibility and API boundary

`src/memebot/eligibility.py` is the shared fail-closed policy used by strategy
decisions, automatic/manual paper entries, the buy simulator, risk assessment,
and holder enrichment. Native discovery records the token mode. Missing mode is
`TOKEN_MODE_UNKNOWN`; a name, ticker, or apparently ordinary trade cannot establish
standard mode. Conflicting evidence containing a Mayhem flag also rejects.

| Evidence | Rejection |
|---|---|
| Mayhem flag | `OUT_OF_SCOPE_MAYHEM` |
| PumpSwap venue/program | `OUT_OF_SCOPE_PUMPSWAP` |
| Complete curve, migration or graduated lifecycle | `MIGRATED_MARKET` |
| Multiple Pump trade events in one transaction | `MULTI_EVENT_AMBIGUOUS` |
| Unknown semantics, unknown/invalid continuity | `STATE_UNKNOWN` |
| Diverged continuity/state | `CONTINUITY_DIVERGED` |
| Missing canonical execution identity | `IDENTITY_INCOMPLETE` |
| Incomplete execution/config proof | `EXECUTION_STATE_INCOMPLETE` |

This version also retains the existing SOL quote requirement. Standard tokens
paired to other quote assets are not executable under this model. This extra
restriction is explicit in the capture (`UNSUPPORTED_QUOTE`); the launch fraction
below therefore distinguishes standard tokens from supported-quote survivors.

Normalized evidence and paper fills record `trading_universe`,
`entry_eligibility_status` and `entry_rejection_reason`. `ENTRY_READY` describes
the universe/state proof only; existing freshness, executable quote, risk,
experiment and calibration gates must also pass. A multi-event flag survives RPC
refresh. This version rejects all multi-trade Pump transactions conservatively,
including transactions involving different mints. No transaction reconstruction
was performed in this phase.

PumpSwap/migration notifications now log rejection without pool-validation RPC.
Normal native subscriptions cover Pump and the Fee program; PumpSwap discovery is
not subscribed. The default config cache reads only Pump Global and Pump FeeConfig,
coalesces callers, and ignores PumpSwap config-generation changes. Excluded trades
do not consume risk queue quotas. Deep risk/holder calls recheck execution proof;
paid PumpPortal control sampling and restored watchlists also check scope first.
Wallet observation remains local database work. None of these entry restrictions
gate sells or existing-position subscription/recovery. Generic RPC recovery may
bootstrap an excluded venue **only for safety recovery of existing exposure**.

Automatic canonical candidate bootstrap is not activated while this runner is
blocked. Removing that prerequisite guard would spend RPC without establishing
usable execution proof. A later standard-only bootstrap duty must be bounded,
coalesced, and ordered after cheap standard/state filtering and before wallet work.

## Standard continuity evidence

The retained trace contains **3,932 standard Pump.fun trade observations**:

| Evaluation | FIRST | EXACT | DIVERGED | UNKNOWN |
|---|---:|---:|---:|---:|
| Production trust, retained trace | 234 | 0 | 8 | 3,690 |
| Trade-only arithmetic, retained trace | 234 | 2,841 | 8 | 849 |
| Production trust, new 60-second capture | 182 | 0 | 0 | 3,451 |
| Trade-only arithmetic, new capture | 182 | 2,873 | 0 | 578 |

Mayhem and PumpSwap observations are absent from these standard statistics.
The capture additionally excludes observed completion/migration and unsupported
quotes. Arithmetic replay deliberately does not claim complete instruction
coverage. It supports deterministic **POST_TRADE** integer transitions when
adjacent standard single-event observations have matching state: buy adds quote
and subtracts tokens; sell reverses those changes in real and virtual reserves.
It does not establish deterministic complete production continuity.

The retained production UNKNOWN reasons are 3,492 `UNKNOWN_NATIVE_INSTRUCTION`,
144 `MULTI_EVENT_AMBIGUITY`, and 54 `TRUNCATED_LOG`. Anonymous native/self-CPI
frames lack enough instruction data to prove they only emit an event. Conservatively
retaining UNKNOWN prevents the arithmetic model from becoming execution proof.

The eight retained standard divergences affect all four reserve dimensions.
Unlike the earlier excluded cohort's virtual-quote-only pattern, these are
consistent with missing ordinary reserve mutations or capture/ordering gaps.
**Their causal mechanism is not proven** by stored evidence. The new capture
had no arithmetic divergences; its short duration does not disprove the older ones.
Cases and exact deltas are in `analysis/standard_pumpfun_validation.json`.

The captures used the earlier same-mint multi-event classification. The deployed
policy now rejects any transaction with multiple Pump trade events. These statistics
are diagnostic counts, not a revised entry calibration population.

## Canonical identity

Canonical bootstrap verifies mint/address/token-program ownership, curve PDA and
Pump ownership, initialized mint and supply, canonical associated token vault,
vault program/mint/authority binding, quote asset, known completion and
non-migrated state, non-regressing account slots, and config references/version.
Default standard bootstrap additionally rejects Mayhem before mint/vault reads.
Global/FeeConfig address, owner, discriminator, full pinned schema and byte hashes
provide config binding. Unknown or partial schemas cannot verify config.

Earlier standard-matched canonical snapshots are retained in the report. They
establish that the checks can succeed; they do not establish current identity or
same-transaction execution state for the new cohort. Separate RPC account batches
at compatible slots are not a transaction/state-sequence boundary. Consequently
**canonical identity is not fully verified for a runnable prospective cohort**.

## Standard fee inputs and truth

The official [Pump Fee program documentation](https://github.com/pump-fun/pump-public-docs/blob/main/docs/FEE_PROGRAM_README.md)
selects bonding-curve fees using FeeConfig tiers and integer market capitalization
from actual mint supply and virtual reserves, falling back to Global fields when
FeeConfig is absent. Therefore Global's creator fee alone is insufficient.

| Input/assumption | Classification |
|---|---|
| Retained Pump Global and Pump FeeConfig bytes, owners, addresses, schemas, versions | VERIFIED_ONCHAIN at recorded slots |
| Retained Pump FeeConfig protocol 95 bps + creator 30 bps tier | VERIFIED_ONCHAIN at recorded slots |
| Config version/tier bound to the exact prospective order state | UNKNOWN |
| Creator override, creator-zero case, cashback/reward routing and destination accounts for that order | UNKNOWN |
| Current simulator's 95/30 components, static supply and integer quote model | ESTIMATED |
| Network/priority/provider fees and fill-latency slippage | ESTIMATED |
| Exact buy/sell rounding against synchronized standard transaction evidence | UNKNOWN |

Normal buy/sell evidence needs the canonical curve and mint supply, exact virtual
and real reserves at the decision boundary, quote mint/decimals, complete/mode and
creator fields, applicable Global/FeeConfig and any creator/fee-sharing bindings,
actual selected protocol/creator components and fee destinations, instruction
variant/input units, integer rounding and reserve caps, and bounded external costs.
These inputs must describe the same execution instant. Account schema completeness
alone does not prove all execution assumptions.

The existing 125 bps simulation was relabeled `ESTIMATED`; the default fee amount
was not silently replaced by Global's 100 bps sum or promoted to on-chain authority.
Production bootstrap keeps `execution_assumptions_verified=False`, so this estimate
cannot authorize the runner. No new PumpSwap fee research was done.

## Funnel, API cost and calibration gate

The new bounded read-only native capture lasted **60.069 seconds**:

| Measurement | Result |
|---|---:|
| Pump launches observed | 32 |
| Standard non-Mayhem launches | 25 (78.125%) |
| Standard supported-SOL-quote survivors | 17 (53.125%) |
| Serious state-eligible candidates | 0 |
| ENTRY_READY executions | 0 |
| HTTP RPC/config/identity/execution refresh reads | 0 / 0 / 0 / 0 |
| Excluded-market deep reads | 0 |
| RPC cost per serious eligible candidate | Undefined: denominator is zero |
| Synchronized eligible disagreement pairs | 0 |

This is a short observed-launch sample, not an estimate of ecosystem prevalence.
Native log subscriptions and delivery still consume provider resources; zero HTTP
reads does not mean zero provider billing. Stream message/subscription counts and
endpoint hashes are retained, but invoice/CU pricing was not inferred. No paid
wallet, quote, reconstruction or config enrichment was performed for excluded launches.

Synchronized disagreement calibration was **not run**, because standard identity,
complete state coverage and per-order fee assumptions are not yet clean. No
slot-only, Mayhem, PumpSwap, migrated, ambiguous, or UNKNOWN observations were
inserted into a disagreement distribution. N=0 and all bands remain null.

`runner-edge-prospective-v1` cannot start now. A later synchronized calibration
is necessary but not sufficient: the state/identity/fee prerequisites, freshness,
exit recovery and existing validation gate must also pass. Remaining blockers
are standard native instruction coverage, the eight causally unresolved retained
divergences, synchronized current canonical/config/reserve evidence, validated
per-order fee behavior, and representative standard-only calibration evidence.
Mayhem mechanics are no longer a runner-readiness requirement.

Historical paper PnL is not retroactively repaired by this scope filter. Results
without consistent execution-state and fee evidence remain unsuitable for
calibrating prospective profitability.
