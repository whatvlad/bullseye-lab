"""Build retained-evidence reports and docs; no provider calls or database writes."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from memebot.research.pumpfun_sequence import reconstruct_transaction

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"
def read(name):
    return json.loads((OUT / name).read_text())
def write(name, report):
    (OUT / name).write_text(json.dumps(report, indent=2) + "\n")

capture, scope, forensic, identity, fees = [read(name) for name in ("state_trust_validation.json", "invalidation_scope.json", "pumpfun_mismatch_classification.json", "identity_bootstrap.json", "fee_config_bootstrap.json")]
categories = "MISSING_TRADE MULTI_EVENT_TRANSACTION VIRTUAL_RESERVE_CHANGE REAL_RESERVE_CHANGE RESERVED_INVENTORY_EFFECT CONFIG_MUTATION MAYHEM_MUTATION MIGRATION DIRECT_ACCOUNT_MUTATION EVENT_ORDERING TRUNCATED_LOG COLLECTOR_LOSS DECODER_ERROR UNKNOWN".split()
forensic["attempted_classification_counts"] = {name: forensic["classification_counts"].get(name, 0) for name in categories}
forensic["counts_are_observed_integer_patterns_not_excluded_hypotheses"] = True
directions = Counter()
for case in forensic["cases"]:
    previous, current = case["previous"], case["row"]
    difference = current["quote_reserve"] - previous["quote_reserve"]
    direction = "buy" if difference > 0 else "sell" if difference < 0 else "UNKNOWN"
    case["direction_from_real_quote_change"] = direction
    directions[direction] += 1
forensic["clusters"].update(direction=dict(directions), native_instruction=dict(Counter(e.get("instruction_name") or "UNKNOWN" for e in forensic["native_sample"].values())), native_transaction_trade_count=dict(Counter(str(e.get("trade_event_count")) for e in forensic["native_sample"].values())), token_age="NOT_RETAINED", graduation_state="NOT_RETAINED", collector_queue_pressure="NOT_RETAINED", unsampled_log_truncation="NOT_RETAINED", delta_magnitude_range={"min_abs": min(abs(c["row"]["delta"]["virtual_quote"]) for c in forensic["cases"]), "max_abs": max(abs(c["row"]["delta"]["virtual_quote"]) for c in forensic["cases"])})
forensic["conclusion"] = "All 117 have an isolated virtual-quote discontinuity. All 16 mismatch trade samples and four sampled predecessors are Mayhem-mode; two exact controls are not. A recurring Mayhem-linked mechanism is supported, but the precise operation/state boundary causing each change is not proven. Ordinary missing trades alone cannot produce an isolated virtual-quote residual while the other three ordinary invariants remain exact."
forensic["causal_mechanism_unknown_count"] = 117
write("pumpfun_mismatch_classification.json", forensic)

block = json.loads(gzip.decompress((ROOT / "research_sessions/reserve-sync-20261001/block-452373150.json.gz").read_bytes()))
signature = "5ZcMFdFPdt98Cg1hWzb9t9KDsbWdUMGKev1Tc49opLLzexJpjbMdtVvfFAmJxChtjYDfZkmuDWBvDfeWVdFAro8A"
tx = next(tx for tx in block["transactions"] if tx["transaction"]["signatures"][0] == signature)
sequence = reconstruct_transaction(tx)
write("pumpfun_multi_event_reconstruction.json", {"source": "retained finalized native block", "slot": 452373150, "signature": signature, "new_rpc_reads": 0, "cases": sequence, "production_promotion": False})

scope["production_global_paths"] = [
    {"path": "pump.run / _publish_health(DISCONNECTED)", "reason": "STREAM_DISCONNECT", "scope": "GLOBAL", "justification": "One socket carries all subscribed native venues; loss cannot be localized further."},
    {"path": "scope_native_mutations/truncation", "reason": "TRUNCATED_LOG", "scope": "VENUE when program known; GLOBAL only without native program evidence", "justification": "Missing log tail can contain native mutations; no silent read-only assumption."},
    {"path": "scope_native_mutations/fee program", "reason": "CONFIG_CHANGE or UNKNOWN_NATIVE_INSTRUCTION", "scope": "GLOBAL config-only if controlling venue unproven", "justification": "Shared fee program may affect both venues; reserves remain observable."},
    {"path": "old production_state_validation research collector", "scope": "GLOBAL", "production_path": False, "justification": "Retained as the previous baseline, not used by the corrected provider."},
]
scope["global_reserve_invalidations"] = sum(r["scope"] == "GLOBAL" and "reserves" in r["dimensions"] for r in scope["ledger"])
scope["global_config_only_invalidations"] = sum(r["scope"] == "GLOBAL" and r["dimensions"] == ["config"] for r in scope["ledger"])
scope["global_unknown_observations"] = capture["unknown_by_scope"].get("GLOBAL", 0)
scope["silent_self_cpi_policy"] = "Parent-native event scopes uncertainty; missing instruction data is never treated as proof of read-only execution."
scope["native_account_resolution"] = "Live logs expose event fields and invocation stack, not transaction writable accounts. Cached market/vault identities resolve requested-account failures. Research native metadata supplies instruction indices/accounts where available. Unknown indices stay null."
write("invalidation_scope.json", scope)

fees["trust_meaning"] = "VERIFIED_ONCHAIN means decoded and bound at the recorded read slot, not continuously verified after subsequent unresolved mutations."
fees["per_market_unknown"] = ["Creator sharing-config and holder-reward/cashback route", "curve-specific custom creator fee and token transfer extensions", "selected fee tier at exact execution state"]
fees["config_cache_policy"] = "One shared cache per process; one coalesced four-account read per invalidation generation. No reads on trade arrival. Capture had 13 generations/read batches, so current uncertainty still causes cache churn."
fees["static_assumptions"] = {"paper_venue_fee_bps": "unchanged existing setting", "slippage": "scenario assumption, not observed fill", "network_and_priority_fees": "existing paper model", "exact_application": False}
write("fee_config_bootstrap.json", fees)
capture["bootstrap_verified_by_venue"] = identity["bootstrap_verified_by_venue"]
capture["bootstrap_config_verified_curves"] = sum(bool(proof.get("identity") and proof["identity"]["config_verified"]) for proof in identity["bootstrap_checks"].values())
capture["no_fee_or_identity_trust_promoted_after_uncertain_mutation"] = True
capture["previous_capture"] = {"observations": 3962, "EXACT": 94, "DIVERGED": 117, "UNKNOWN": 3323, "FIRST_OBSERVATION": 428, "elapsed_seconds": 20.6675, "comparison": "Different sessions; not an apples-to-apples feed reliability comparison."}
capture["initial_validation_attempt"] = {"elapsed_seconds": 71.2850746, "observations": 9717, "rpc_calls": 1, "bootstrap_candidates": 0, "finding": "Silent self-CPI frames initially unresolved at venue scope; corrected to parent-market scope before final capture."}
capture["all_phase_rpc_reads"] = len(forensic["provider_requests"]) + len(identity["supplement_rpc_calls"]) + capture["rpc_calls"] + 1
capture["aggregate_declared_request_caps"] = 20 + 60 + 60 + 16 + 16
capture["read_only_method_counts"] = dict(Counter(call["method"] for call in forensic["provider_requests"] + identity["supplement_rpc_calls"] + capture["provider_requests"]))
capture["read_only_method_counts"]["getMultipleAccounts"] += 1  # Initial attempt's only config bootstrap.
capture["official_schema_http_reads"] = 3
capture["capture_source_sha256"] = "NOT_RETAINED; final source hashes are recorded by the separate verification report."
write("state_trust_validation.json", capture)

docs = {
"INVALIDATION_SCOPING.md": f"""# Invalidation scoping

The corrected provider uses event market bindings, canonical mint-to-curve derivation, the native invocation stack and cached account/vault identities. Live `logsSubscribe` does not expose transaction writable accounts or instruction data. Those are used only in bounded research reads. Missing transaction/instruction indices are null, never inferred from event ordinal.

| Trigger | Minimum safe scope | Trust invalidated |
|---|---|---|
| Unsupported instruction with decoded pool/curve/mint binding | POOL / MARKET | Reserves, identity and config unless IDL proves narrower writes |
| Silent self-CPI with proven native parent market | POOL / MARKET | Uncertain mutation retained; never silently ignored |
| Native program known, market unresolved | VENUE | Relevant dimensions |
| Truncated logs with program evidence | VENUE | Reserves |
| Truncation without program evidence | GLOBAL | All dimensions |
| Shared fee mutation with unproven venue | GLOBAL | Config only; observational reserves remain usable |
| Shared WebSocket disconnect | GLOBAL | Lost mutations across subscribed venues |
| Integer continuity break / multi-event ambiguity | MARKET | Reserve history; one coalesced repair |
| Requested RPC account failure | Cached affected markets | Reserves; identity is cleared only on binding failure |
| Owner/address/migration/config mismatch | Identified market or config venue | Proven affected dimensions |

Every tracker invalidation records reason, scope, program, signature, slot, known indices, affected markets, identity-known flag, repair-queued flag and dimensions. Original invalidation cause survives later consistent ticks. The bounded ledger and coalesced pending dictionary avoid unbounded in-memory growth; the passive run retains its full 39,594-record ledger.

The final capture has {scope['active_invalidations']:,} active invalidations. {scope['single_market_invalidations']:,} ({scope['single_market_fraction']:.2%}) affect exactly one market. There are {scope['global_reserve_invalidations']} global reserve invalidations and {scope['global_config_only_invalidations']} deliberately retained global config-only invalidations. GLOBAL causes zero UNKNOWN trade observations; remaining UNKNOWN is attributed to MARKET/POOL/VENUE.

The pure-scope replay reproduces every held local status, with the same events, native mutation coverage and transaction order. It finds **zero UNKNOWN reduction attributable to scoping alone**. The old-helper versus new-helper comparison adds invocation-frame coverage and is not a pure scope comparison. No improved feed-reliability claim is made. The previous 3,962-event capture lacks native mutation frames and cannot be reconstructed exactly without additional chain acquisition.

Code: `providers/solana/invalidation.py`, `market_state.py`, `providers/solana/pump.py`; evidence: `analysis/invalidation_scope.json` and `analysis/replay_invalidation_scope.py`.
""",
"PUMPFUN_CONTINUITY_FORENSICS.md": f"""# Pump.fun continuity forensics

All **117** retained mismatches on **22 markets**, **117 signatures**, and **36 slots** have one integer residual: virtual quote. Real quote, real token and virtual token continuity match exactly. There are 60 positive and 57 negative virtual-quote residuals. Every case and every attempted category is recorded in `analysis/pumpfun_mismatch_classification.json`; zero counts in other categories mean not established, not ruled out.

Bounded native evidence covers 16 mismatch trades (largest residuals and market clusters), two deterministic random exact controls and four largest-mismatch predecessors: 22 transaction reads. All sampled mismatch trades and predecessors are Mayhem-mode; both exact controls are non-Mayhem. Sampled instructions are ordinary buy/sell variants, including a CreateV2 + BuyV2 predecessor. No selected predecessor/current instruction log proves an intervening SetMayhemVirtualParams call. The stored bytes support the decoded reserve values, but not the exact account-state boundary behind every change.

This supports a recurring **Mayhem-linked virtual-quote mechanism or semantics difference**, rather than evidence of 117 independent feed losses. The precise causal operation remains **UNKNOWN for all 117**. Token age, full unsampled transaction structure, graduation state, queue pressure and unsampled truncation evidence were not retained by the older collector; those fields are explicitly unavailable. The new capture retains direction/mode/instruction, source slot, receipt time, multi-event flag, truncation flag and local queue depth.

For an ordinary trade with direction d=+1 for buy and -1 for sell, integer quote movement Q and token movement T:

```
real_quote'    = real_quote    + d*Q
virtual_quote'= virtual_quote + d*Q
real_token'   = real_token    - d*T
virtual_token'= virtual_token - d*T
```

Therefore virtual_quote-real_quote and virtual_token-real_token stay constant under ordinary trades; token_total_supply also stays constant. Missing ordinary trades alone cannot produce the isolated virtual-quote residual while the other three ordinary invariants remain exact. Nonordinary virtual updates, Mayhem semantics and incorrect boundary interpretation remain plausible. No percentage tolerance is used.

Physical curve-vault inventory is distinct from real sellable reserves. `physical_vault - real_token` is an inventory offset only when bindings and a coherent state sequence are proven. It is not equal to `virtual_token - real_token`. Supply minus real reserves is not circulating supply without further mint/vault evidence. Completion is set when ordinary buying exhausts real sellable tokens; migration changes venue/authority and requires rebootstrap. Creator/config updates and native SetMayhemVirtualParams can invalidate other assumptions independently of trade flow.

Generic research reconstruction requires untruncated successful native metadata, canonical curve/vault binding, top-level ordinary instruction/event order, matching emit-CPI payloads, no other curve/vault top-level mutation, exact real/virtual transitions and physical token/lamport totals. Any missing proof remains UNKNOWN. The retained three-buy transaction at slot 452373150 passes with zero residuals and reserved inventory **206,900,000,000,000** raw tokens; its virtual-token offset is **279,900,000,000,000**, a different quantity. There is no special-case mint/signature logic. Production multi-event trades remain UNKNOWN until an instruction-aware stream or an equivalent bounded transaction-proof path supplies the metadata.

Research code: `research/pumpfun_sequence.py`; evidence: `analysis/pumpfun_multi_event_reconstruction.json`. Official semantics and pinned IDLs: [Pump documentation](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md), [Pump IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json). Mayhem attribution above is an inference from retained native evidence, not an official guarantee.
""",
"CANONICAL_IDENTITY_BOOTSTRAP.md": """# Canonical identity bootstrap

Addresses are derived with solders' Solana PDA implementation, not custom elliptic-curve code. Official current IDLs are retained under `providers/solana/idl/` and SHA-256 pinned by `idl_schema.py`.

Pump.fun checks the `[bonding-curve,mint]` PDA, account/program ownership, native-SOL quote identity, completion state, mint address/owner/initialization/supply, canonical token-program-specific curve ATA, vault mint/authority/address and non-regressing account slots. Creator and fee/global references are retained. A complete curve requires migration recovery rather than curve execution. Unsupported quotes, ambiguous supply/bindings and legacy missing assumptions cannot become exact execution evidence.

PumpSwap checks `[pool,index_u16_le,creator,base_mint,quote_mint]` PDA and bump, base/quote orientation, canonical index-zero creator derived from Pump `[pool-authority,base_mint]`, both token-program-specific pool ATAs, vault mint/authority/address, initialized mint owners/addresses, a complete canonical source curve and its creator relationship. The virtual quote offset comes from the decoded pool account; it is added exactly once to the physical quote-vault balance. Arbitrary internally consistent pools are rejected as canonical.

The passive capture bootstrapped **12 Pump.fun curves** and accepted **11 reserve reconciliations**; one was rejected because the stream advanced beyond the RPC snapshot. Final stricter address guards were additionally validated on one curve and three PumpSwap pools. All three sampled pools pass canonical binding checks. These are sampled proofs at recorded read slots, not verification of every market.

At capture end, current canonical/config trust was zero: later unknown native invocations invalidated the cached proofs. `bootstrap_verified_by_venue` and current trust are separate fields in `analysis/identity_bootstrap.json`. A successful past bootstrap must not be presented as continuously verified identity.

Identity/config bootstraps are cached and invalidated by migration, owner/address/creator/offset mismatch or explicit/uncertain native updates. Trades never trigger per-event reads. Stable identity avoids the auxiliary mint/source-curve batch on subsequent reserve refreshes; config uses a shared four-account batch per generation. The observed uncertain-invocation/config churn still limits these potential savings.

Account batches are source-slot bounded, not transaction-boundary synchronized. Curve/vault reads at different slots cannot prove a historical reserved-inventory invariant; the report labels this limitation explicitly. Source wall-clock time is not invented from RPC receipt time.

Implementation: `providers/solana/canonical.py`, `bootstrap.py`, `paper/market_refresh.py`. [Official PumpSwap IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_amm.json), [official Pump IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json).
""",
"FEE_CONFIG_BOOTSTRAP.md": """# Fee and config bootstrap

Four derived accounts were owner/address/discriminator validated and completely decoded at recorded slots: Pump Global, PumpSwap GlobalConfig, and the Pump fee-program FeeConfig PDAs for each venue. Every field, raw-account version hash and source slot is retained in `analysis/fee_config_bootstrap.json`.

VERIFIED_ONCHAIN inputs include initial curve reserves/supply, Pump fee and creator basis points, recipient lists, migration fee, Mayhem/cashback/holder-reward switches and authorities; PumpSwap LP/protocol/creator basis points, disable flags, recipients and boost authority/settings; and both fee-program flat/stable/exotic fee schedules and market-cap tiers. The captured Pump schedule has one dynamic tier and PumpSwap has 25. No basis points are copied into strategy thresholds or disagreement bands.

These account facts do **not** prove which schedule/tier, creator sharing or holder-reward/cashback route applies to a particular order at its historical instant. Per-curve configurable creator fees and Token-2022 extensions are not fully integrated. Exact executable rounding, network/priority fees, slippage and Mayhem/boost execution behavior remain unverified. Existing paper fee/slippage settings remain STATIC_ASSUMPTION, not VERIFIED_ONCHAIN execution. Missing per-market inputs are UNKNOWN.

The shared cache coalesces concurrent reads and hashes account bytes into version identifiers. An invalidation generation queues one refreshed four-account batch on the next admitted bootstrap/entry/exit duty; no trade invokes RPC. The passive run used 13 such batches amid native uncertainty. Failed or incomplete config decoding cannot yield an exact config version. Trailing schema omissions are retained as unknown fields, never silently filled into execution proof.

Observational reserve tracking does not require fee config. Reserves reconciled does not imply fee/config verified. Execution assumption verification stays false, so price evidence cannot be promoted to full execution trust merely because a config account decoded successfully. VERIFIED_ONCHAIN is a snapshot-at-slot fact, not a promise after unresolved updates.

Source schemas: [official fee IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_fees.json), [PumpSwap IDL](https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump_amm.json). Implementation: `providers/solana/bootstrap.py`; schema versions are SHA-256 pinned in `idl_schema.py`.
""",
"STATE_TRUST_MODEL.md": f"""# State trust model and readiness

Observational trust, canonical identity, config facts, execution assumptions and state divergence are independent dimensions. `NormalizedMarketState.evidence()` and serialized paper-fill evidence expose those dimensions. The legacy HEALTHY execution gate is retained only for complete proven execution prerequisites; it does not replace the independent flags.

| Dimension | Requirement / use |
|---|---|
| OBSERVATIONAL_HEALTHY | Proven normalized reserve semantics plus FIRST/EXACT/RPC_VALIDATED continuity; momentum may use the reserve price |
| OBSERVATIONAL_INCOMPLETE / UNKNOWN | Missing/ambiguous history; reserve-dependent features are unavailable, not zero or stable |
| EXECUTION_IDENTITY_VERIFIED | Canonical account bindings actually pass; can be invalidated independently |
| EXECUTION_CONFIG_VERIFIED | Bound on-chain config version decoded; no claim of exact fee application |
| execution_assumptions_verified | Exact executable assumptions additionally proven; remains false |
| DIVERGED | Nonzero integer residual; local repair required |

Repairs are market-coalesced and admitted by duty/budget. Stable ticks cannot erase a broken history. An older RPC slot cannot overwrite newer stream state. Reserve repair restores only what was proved. Open-position exits retain their prioritized RPC fallback path and cannot use rejected/degraded RPC as a valid simulated fill. No worker, order, paper position or experiment was started in this pass.

Final passive capture: **{capture['elapsed_seconds']:.2f}s**, **{capture['total_observations']:,} trades**, **{capture['markets']} markets**, capped at 150,000 native messages. Counts: FIRST 745, EXACT 6, DIVERGED 618, UNKNOWN 16,934. UNKNOWN attribution: POOL 12,613; MARKET 3,958; VENUE 363; GLOBAL 0. There are 778 coalesced pending repairs; 12 admitted bootstraps, 11 accepted reconciliations. Successful bootstrap proof and current trust are deliberately separate.

RPC: **37 calls / 12 candidates = 3.0833 per candidate**, **0.6066 per observed launch**, no per-event calls. The 37 comprise 13 shared config batches and 24 curve/identity reads. Across the bounded forensic sample, initial validation, final capture and supplemental stricter canonical checks: **{capture['all_phase_rpc_reads']} read-only Solana requests**. Three public schema downloads are separate. No new disagreement bands or strategy thresholds were configured.

The old capture (3,962 trades, 94 EXACT, 117 DIVERGED, 3,323 UNKNOWN) and new capture are different sessions/durations. The retained same-coverage replay reproduces all local statuses exactly and shows **0 UNKNOWN reduction caused by scope alone**. Narrowing prevents cross-market collateral invalidation but unresolved silent native self-CPIs still occur on nearly every traded market. No better feed reliability is claimed.

| Readiness question | Evidence-based answer |
|---|---|
| Cause of the 117 Pump.fun mismatches | Isolated virtual-quote changes; sampled evidence supports a recurring Mayhem link; exact causal mechanism unproven |
| Remaining UNKNOWN | 117 forensic causal mechanisms; separately 16,934 UNKNOWN observations in the new capture |
| Global invalidation eliminated | No global reserve invalidations/UNKNOWN in this capture; 18 necessary global config-only invalidations remain |
| Single-market scoping | 18,806 / 19,616 active invalidations = 95.87% |
| Pump.fun canonical identity | 12 sampled bootstraps pass; later uncertainty invalidates current trust |
| PumpSwap canonical identity | Three sampled pools pass final canonical/migration/vault checks |
| Fee/config inputs verified | Four global/fee accounts, full schedules, flags, authorities and byte-hash versions at source slots |
| Still estimated/unproven | Actual tier/routing/rounding, extensions, slippage/fees and synchronized execution state |
| RPC per candidate | 3.0833 in final passive capture; cold pool bootstrap requires extra binding reads |
| Synchronized disagreement calibration ready | Bounded transaction-reconstruction research can proceed; broad synchronized calibration is not yet trustworthy |
| runner-edge-prospective-v1 | **BLOCKED** |

Remaining blockers: silent CPI instruction data is absent from live logs; exact Mayhem virtual-state boundary is unproven; direct vault changes and loss layer are not comprehensively captured; RPC is SLOT_ONLY rather than transaction/state-sequence synchronized; per-order fee/execution assumptions remain incomplete; representative synchronized residual evidence is insufficient; disagreement bands stay intentionally unconfigured. Historical PnL is not retroactively repaired or promoted by these new proofs.

Evidence: the five requested JSON reports, `pumpfun_multi_event_reconstruction.json`, and `state_trust_verification.json`. Regression coverage includes local/venue/global invalidation, original cause retention, canonical mismatch, config version/cache change, reserve-only repair, multi-event ambiguity, incomplete-entry refusal and safe observational features.
""",
}
for name, content in docs.items():
    (ROOT / "docs" / name).write_text(content, encoding="utf-8")
print(json.dumps({"docs": list(docs), "phase_rpc_reads": capture["all_phase_rpc_reads"], "forensic_causal_unknown": 117, "pure_scope_unknown_reduction": 0}))
