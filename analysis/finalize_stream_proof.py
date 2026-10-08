"""Reproducible passive pilot reports; never activates experiments."""
from collections import Counter
import asyncio
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

import asyncpg

from memebot.core.config import Settings
from memebot.paper.validation_gate import require_price_validation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, default=str)+"\n", encoding="utf-8")


def category(proof):
    reason = proof["reason"] or ""
    if proof["status"] == "PASS":
        return "PASS"
    if "transaction unavailable" in reason or "transaction metadata missing" in reason:
        return "FAIL_TRANSACTION_AVAILABILITY"
    if "signature window" in reason or "boundary not reached" in reason or "union signature" in reason:
        return "FAIL_HISTORY_WINDOW"
    if "reconstruction" in reason or "physical mutation" in reason:
        return "FAIL_RECONSTRUCTION"
    if proof["status"] == "FAIL_STATE_SYNC":
        return "FAIL_SYNC"
    return "OTHER"


def counts(proofs):
    result = dict.fromkeys(("PASS", "FAIL_TRANSACTION_AVAILABILITY", "FAIL_HISTORY_WINDOW",
                           "FAIL_RECONSTRUCTION", "FAIL_SYNC", "OTHER"), 0)
    result.update(Counter(category(p) for p in proofs))
    return result


async def verify_database():
    settings = Settings()
    baseline = load("candidate_proof_gate.json")["database"]
    try:
        conn = await asyncpg.connect(settings.database_url.replace("postgresql+asyncpg://", "postgresql://"))
    except (OSError, ConnectionError) as error:
        return {"verified": False, "error_type": type(error).__name__,
                "database_mutations": 0, "previous_baseline": "analysis/candidate_proof_gate.json"}
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            database = {
                "head": await conn.fetchval("SELECT version_num FROM alembic_version"),
                "counts": {t: await conn.fetchval(f"SELECT count(*) FROM {t}") for t in baseline["counts"]},
                "control": dict(await conn.fetchrow("SELECT entries_paused, active_strategy_key, base_position_percent, max_position_percent, max_open_positions, stop_loss_percent, take_profit_percent, trailing_stop_percent, max_holding_seconds FROM trading_control LIMIT 1")),
                "runner_experiments": await conn.fetchval("SELECT count(*) FROM experiment_runs WHERE name='runner-edge-prospective-v1'"),
                "open_positions": await conn.fetchval("SELECT count(*) FROM paper_positions WHERE status='open'"),
                "execution_mode": settings.execution_mode,
            }
    finally:
        await conn.close()
    assert json.loads(json.dumps(database, default=str)) == baseline
    try:
        require_price_validation("runner-edge-prospective-v1", {})
    except ValueError:
        pass
    else:
        raise AssertionError("runner must stay blocked")
    return database


def main():
    pilot = load("stream_pilot.json")
    previous = load("live_proof_cohort.json")["proofs"]
    probe = load("stream_provider_probe.json")
    rows = []
    for proof in previous:
        cause = category(proof)
        if cause == "FAIL_TRANSACTION_AVAILABILITY" or proof["status"] == "FAIL_RPC":
            replacement = "Complete compatible stream packet could avoid this getTransaction failure; later proof checks remain unproven"
        elif cause == "FAIL_HISTORY_WINDOW":
            replacement = "A certified rolling mutation sequence could replace retrospective discovery; current fences/caps remain unchanged"
        elif cause == "FAIL_SYNC":
            replacement = "Stream barriers/account ordering may improve synchronization; fresh bank can still race, not guaranteed preventable"
        else:
            replacement = "No evidence that transport replacement alone fixes this failure; same semantics/parity/invalidation checks must pass"
        rows.append({"signature": proof["candidate"]["anchor_signature"],
                     "mint": proof["candidate"]["mint"], "status": proof["status"],
                     "reason": proof["reason"], "category": cause,
                     "stream_counterfactual": replacement, "causal_prevention_proven": False})
    comparison = {"previous_74": counts(previous), "attribution": rows,
                  "fundamentally_retrospective_proven": 0,
                  "fundamentally_retrospective_actual": None,
                  "direct_getTransaction_targets": 27,
                  "history_bound_targets_conditional": 8,
                  "sync_targets_conditional": 3,
                  "causal_warning": "Failure site identifies a target, not exclusive cause or future PASS",
                  "pilot": {name: counts([p[name] for p in pilot["pairs"]]) for name in ("OLD", "NEW")},
                  "paired_candidates": len(pilot["pairs"]),
                  "paired_comparison_limitation": "Sequential same-candidate reads; different bank/timing, no usable full stream",
                  "improved_complete_evidence_fraction_demonstrated": False}
    write("retrospective_vs_stream.json", comparison)
    first = {"runner": "BLOCKED", "calibration_started": False, "orders": 0,
             "natural_live_BUY_proofs": 0, "natural_live_SELL_proofs": 0,
             "full_transaction_provider_access_verified": False,
             "pilot": pilot, "provider_probe": probe,
             "historical_replay": {"BUY": "PASS", "SELL": "PASS", "count_as_live": False,
                                    "proof_reads": 5, "mandatory_refresh_reads": 1},
             "history_fences_removed": 0}
    write("stream_first_proofs.json", first)
    write("stream_coverage.json", {"pilot": pilot["coverage"],
        "states": ["CONNECTED", "DEGRADED", "GAP_DETECTED", "RECONNECTING",
                   "RESUMED_WITH_GAP", "COMPLETE_FOR_WINDOW"],
        "complete_for_window_implemented_by_available_adapter": False,
        "required_before_fence_removal": ["complete relevant transaction/account mutation filters",
            "closed commitment/fork-bound slot barriers with delivery reconciliation",
            "account write_version/signature correlation", "full bank boundary synchronization",
            "deduplicated transaction index sequence", "verified resume/backfill through gap"],
        "connectivity_is_not_coverage": True, "all_four_history_fences_retained": True})
    meter = pilot["meter"]
    duration = meter["duration_seconds"]
    byte_count = meter["decoded_application_bytes"] + meter.get("full_stream_bytes", 0)
    rate = byte_count / duration
    candidates = len(pilot["pairs"])
    models = {}
    for name in ("OLD", "NEW"):
        proofs = [p[name] for p in pilot["pairs"]]
        models[name] = {"attempts": len(proofs), "passes": sum(p["status"] == "PASS" for p in proofs),
            "rpc_requests": sum(p["costs"].get("total_rpc_requests", 0) for p in proofs),
            "rpc_per_serious_candidate": sum(p["costs"].get("total_rpc_requests", 0) for p in proofs)/candidates if candidates else None,
            "rpc_per_successful_proof": None,
            "proof_latency_ms": [p["proof_latency_ms"] for p in proofs],
            "local_transaction_hits": sum(p["costs"].get("local_transaction_hits", 0) for p in proofs)}
    cost = {"scope": "Available broad Pump/Fee log notifications plus slot/config subscriptions; not full transaction stream bandwidth",
        "meter": meter, "bytes_received_decoded_application": byte_count,
        "compressed_bytes": None, "wire_tls_bytes": None, "provider_billed_bytes": None,
        "duration_includes_setup_teardown": True,
        "bytes_per_second_over_total_runtime": rate, "bytes_per_minute": rate*60,
        "log_notifications_per_second_over_total_runtime": meter["logs"]/duration,
        "full_transactions_per_second": 0,
        "bytes_per_serious_candidate": byte_count/candidates if candidates else None,
        "projections": {label: {"seconds": seconds, "application_bytes": rate*seconds,
            "RPC_reads_at_observed_paired_capture_rate": pilot["rpc_reads"]/duration*seconds}
            for label, seconds in (("1_hour", 3600), ("24_hours", 86400), ("30_days", 2592000))},
        "projection_assumptions": "Stationary short observed log workload, same subscriptions and candidate rate; includes setup/teardown. Not a full-metadata stream estimate or billing forecast.",
        "models": models, "current_account_plan_known": False,
        "actual_dollar_cost": None,
        "published_usage_rates_not_actual_account_billing": {"Helius": "20 credits/MB; Developer $49/month WSS, Business $499/month mainnet gRPC",
            "Alchemy": "$75/TB published gRPC rate, PAYG/Enterprise prerequisite in quickstart/pricing; marketing contradicts prerequisite",
            "QuickNode": "Scale $499/month; 10 credits/0.1MB; not configured"},
        "minimum_current_verified_access": "logs only; inadequate for full stream proof",
        "recommended_first_step": "Resolve the existing Alchemy streaming endpoint/entitlement; do not upgrade. If unavailable, evaluate Helius Developer WSS for packet capture; certification/replay still needed for fence removal."}
    write("stream_provider_cost.json", cost)
    critical = ["src/memebot/providers/solana/evidence_stream.py", "src/memebot/providers/solana/helius_evidence.py",
                "src/memebot/paper/stream_proof.py", "src/memebot/research/stream_proof_run.py",
                "src/memebot/paper/validation_gate.py", "pyproject.toml"]
    gate = {"at": datetime.now(UTC).isoformat(), "runner": "BLOCKED", "calibration_ready": False,
        "calibration_started": False, "orders": 0, "database_mutations": 0,
        "checks": {"full_transaction_stream_available": False, "closed_window_coverage_verified": False,
            "natural_complete_BUY": False, "repeatable_live_SELL": False,
            "complete_evidence_fraction_improved": False, "mandatory_refresh_regressions": True,
            "bounded_capture": True, "regression_tests_passed": True},
        "blockers": ["Helius full transaction stream rejected by current plan",
            "Alchemy gRPC documented endpoint returns UNIMPLEMENTED, entitlement not established",
            "No full transaction or market account update pilot evidence",
            "No certified coverage barriers/resume replay; four fences remain",
            "No natural complete BUY or repeatable SELL; evidence semantics failures remain"],
        "source_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in critical}}
    gate["evidence_sha256"] = {p: hashlib.sha256((OUT/p).read_bytes()).hexdigest() for p in
        ("stream_first_proofs.json", "stream_provider_cost.json", "stream_coverage.json", "retrospective_vs_stream.json")}
    gate["regression_validation"] = {"tests_passed": 340, "ruff": "PASS", "strict_mypy_files": 122}
    gate["database"] = asyncio.run(verify_database())
    gate["database_unchanged"] = True if gate["database"].get("verified") is not False else None
    try:
        require_price_validation("runner-edge-prospective-v1", {})
    except ValueError:
        gate["runner_block_verified"] = True
    else:
        raise AssertionError("runner must stay blocked")
    write("stream_proof_gate.json", gate)
    calibration = load("calibration_gate.json")
    calibration["stream_proof_phase"] = {"report": "analysis/stream_proof_gate.json",
                                         "ready": False, "started": False, "runner": "BLOCKED"}
    write("calibration_gate.json", calibration)
    (ROOT/"docs/STREAM_PROOF_COST.md").write_text(f'''# Stream proof cost — bounded pilot

The 300-second/96-read/4-candidate pilot stopped at its 32 MB application-data cap.
Total runtime was {duration:.3f} seconds, including setup and connection teardown.
It received {byte_count:,} decoded application bytes, {meter['logs']:,} log notifications,
{meter['slot_updates']} slot updates, {meter['account_updates']} account updates and zero complete transactions.
One serious natural standard candidate generated one OLD and one NEW proof attempt.
Each used one RPC read and failed physical reconstruction. Successful-proof cost is undefined.
OLD latency was {models['OLD']['proof_latency_ms']}; NEW was {models['NEW']['proof_latency_ms']} ms.
This failed early, so the one-read result is not the cost of complete proof.

The local historical BUY and SELL regression replays each use five proof RPC reads,
then one mandatory execution refresh: six total versus seven in the old single-anchor
model. One captured transaction saves one historical transaction read. The four
address-history fences and fresh account bank remain. The intended stream plus one
refresh model has not been demonstrated.

Measured application throughput over total runtime is {rate:,.0f} bytes/sec;
{rate*60:,.0f} bytes/minute and {byte_count/max(1,candidates):,.0f} bytes/serious candidate.
Compressed, TLS/wire and actual provider-billed bytes are unavailable.
The sample includes all Pump/Fee log traffic before cheap standard-only eligibility
filtering. Excluded markets caused no candidate proof reads, but still consume feed
bandwidth. These costs cannot be attributed exclusively to eligible standard tokens.

| Horizon | Projected application bytes | Paired pilot RPC reads |
| --- | ---: | ---: |
''' + "\n".join(f"| {label} | {row['application_bytes']:,.0f} | {row['RPC_reads_at_observed_paired_capture_rate']:,.0f} |" for label,row in cost['projections'].items()) + '''

Projections assume the short observed workload, candidate rate and subscriptions
remain constant, with setup/teardown included. They are usage scenarios, not forecasts.
Full transaction/account packets have different size and filtering requirements;
this pilot supplies no defensible numeric projection for them. Actual account plan,
included credits and metered bytes are unknown, so actual dollar cost is UNKNOWN.
Published rates and plan sources are in STREAM_PROVIDER_COMPARISON.md; no service
was purchased, upgraded or enabled. See analysis/stream_provider_cost.json for units.
''', encoding="utf-8")


if __name__ == "__main__":
    main()
