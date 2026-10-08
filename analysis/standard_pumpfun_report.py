"""Retained standard-only evidence, no provider calls or database writes."""
import json
from collections import Counter
from pathlib import Path

from memebot.market_state import MarketStateTracker
from memebot.providers.solana.pump_idl import PumpTrade

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"
retained = json.loads((OUT / "state_trust_validation.json").read_text())
fresh = json.loads((OUT / "standard_pumpfun_capture.json").read_text())
rows = [row for row in retained["observations"]
        if row["venue"] == "pump_fun" and row["raw_event"].get("is_mayhem_mode") is False]
tracker = MarketStateTracker(capacity=20000)
arithmetic = Counter()
cases = []
for row in rows:
    event = PumpTrade(**row["raw_event"])
    result = tracker.observe(event, market=row["market"], slot=row["state_slot"],
        signature=row["last_signature"], ordinal=row["last_event_ordinal"],
        multi_event_unknown=row["multi_event"])
    arithmetic[result.continuity_status] += 1
    if result.continuity_status == "DIVERGED":
        cases.append({"market": row["market"], "signature": row["last_signature"],
                      "slot": row["state_slot"], "delta": result.delta,
                      "cause": "UNKNOWN; consistent with missing ordinary reserve mutations",
                      "causality_proven": False})
old_fees = json.loads((OUT / "fee_config_bootstrap.json").read_text())["accounts"]
identities = json.loads((OUT / "identity_bootstrap.json").read_text())
standard_markets = {row["market"] for row in rows}
proofs = {market: value for market, value in identities["bootstrap_checks"].items()
          if market in standard_markets}
report = {
    "scope": "STANDARD_PUMP_FUN_ONLY", "runner": "BLOCKED",
    "capture": {key: value for key, value in fresh.items()
                if key not in {"observations", "streams"}},
    "launch_fraction_limitation": "60-second sample, not population prevalence; SOL quote only",
    "retained_standard_observations": len(rows),
    "retained_trusted_counts": dict(Counter(row["continuity_status"] for row in rows)),
    "retained_arithmetic_counts": dict(arithmetic),
    "retained_arithmetic_only": True,
    "retained_multi_event_policy": "same-mint ambiguity; production now rejects any multi-trade Pump transaction",
    "standard_divergences": cases,
    "mismatch_causes_understood": False,
    "production_unknown_reasons": dict(Counter(
        row.get("invalidation_reason") or row.get("reason") for row in rows
        if row["continuity_status"] == "UNKNOWN")),
    "post_trade_semantics": "Supported by exact integer transitions; complete native coverage not proven",
    "prior_standard_identity_snapshots": proofs,
    "current_identity_fully_verified": False,
    "identity_limitation": "Earlier canonical snapshots are not sequence-synchronized and not current proof",
    "standard_fee_config_only": {key: old_fees[key] for key in ("pump_global", "pump_fee")},
    "fee_input_classification": {
        "canonical_global_and_fee_config_account_bytes_at_retained_slots": "VERIFIED_ONCHAIN",
        "owner_PDA_discriminator_schema_config_version": "VERIFIED_ONCHAIN",
        "dynamic_tier_protocol_95_creator_30_in_retained_pump_fee": "VERIFIED_ONCHAIN",
        "current_or_historical_order_config_version_and_tier_binding": "UNKNOWN",
        "per_curve_creator_fee_cashback_reward_routing": "UNKNOWN",
        "integer_quote_model_95_30_and_static_supply": "ESTIMATED",
        "network_priority_and_provider_fees": "ESTIMATED",
        "rounding_fee_boundaries_verified_against_synchronized_standard_orders": "UNKNOWN",
    },
    "fee_assumptions_sufficient_for_runner": False,
    "synchronized_disagreement_calibration_possible_now": False,
    "synchronized_eligible_pairs": 0,
    "calibration_status": "NOT_RUN_PREREQUISITES_UNMET",
    "disagreement_distribution": {"N": 0, "median": None, "p99": None},
    "bands_configured": False,
    "remaining_blockers": [
        "Native instruction coverage unresolved for standard events; arithmetic EXACT is not execution proof",
        "Eight retained standard reserve divergences lack causal proof",
        "Current canonical identity/config/curve state lacks synchronized transaction boundary",
        "Per-order dynamic fee selection, curve overrides and rounding need synchronized standard validation",
        "No representative standard-only synchronized disagreement distribution; bands intentionally unset",
        "Automatic bounded standard candidate bootstrap prerequisite duty is not activated while runner blocked",
    ],
    "fee_reference": "https://github.com/pump-fun/pump-public-docs/blob/main/docs/FEE_PROGRAM_README.md",
}
(OUT / "standard_pumpfun_validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: report[key] for key in ["retained_standard_observations",
    "retained_trusted_counts", "retained_arithmetic_counts", "production_unknown_reasons",
    "current_identity_fully_verified"]}, indent=2))
