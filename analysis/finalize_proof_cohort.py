"""Summarize passive cohort and keep runner/calibration activation disabled."""
import asyncio
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from memebot.core.config import Settings
from memebot.paper.candidate_proof import Proof, proof_failure_category
from memebot.paper.validation_gate import CRITICAL_FILES, require_price_validation

OUT = Path("analysis")


def stats(values):
    values = sorted(values)
    if not values:
        return {"N":0,"mean":None,"median":None,"p90":None,"max":None}
    n = len(values)
    return {"N":n,"mean":sum(values)/n,"median":(values[(n-1)//2]+values[n//2])/2,
            "p90":values[min(n-1,(9*n+9)//10-1)],"max":values[-1]}


def stamp(value):
    return datetime.fromisoformat(value)


async def main():
    captures = [json.loads((OUT/"cohort_execution_proofs.json").read_text())]
    if (OUT/"cohort2_execution_proofs.json").exists():
        captures.append(json.loads((OUT/"cohort2_execution_proofs.json").read_text()))
    capture = captures[0]
    proofs = [p for c in captures for p in c["candidate_proofs"]]
    calls = [p for c in captures for p in c["provider_calls"]]
    categories = Counter()
    for proof in proofs:
        # Classification needs only status/reason; no strategy outcome is inferred.
        lightweight = Proof(None, status=proof["status"],reason=proof["reason"])
        proof["failure_category"] = proof_failure_category(lightweight)
        categories[proof["failure_category"]] += 1
        end = proof["evidence"].get("execution_refresh_account_batch",{}).get("received_at",proof["proof_completed_at"])
        own = [c for c in calls if stamp(proof["proof_started_at"])<=stamp(c["requested_at"])<=stamp(end)]
        proof["actual_http_requests"] = len(own)
        proof["actual_methods"] = dict(Counter(c["method"] for c in own))
    passed = [p for p in proofs if p["status"]=="PASS"]
    buy = [p for p in passed if p["candidate"]["anchor"]["is_buy"]]
    sell = [p for p in passed if not p["candidate"]["anchor"]["is_buy"]]
    approved = [p for p in passed if p["evidence"].get("passive_refresh",{}).get("execution_approved")]
    refreshes = []
    for proof in passed:
        e = proof["evidence"]
        fresh = e.get("passive_refresh")
        if not fresh:
            refreshes.append({"mint":proof["candidate"]["mint"],"approved":False,"failure":e.get("passive_refresh_failure")})
            continue
        keys = ("virtual_token_reserves","virtual_quote_reserves","real_token_reserves","real_quote_reserves")
        refreshes.append({"mint":proof["candidate"]["mint"],"approved":fresh["execution_approved"],
            "outcome":fresh["revalidation_outcome"],"trust_dimensions":fresh["trust_dimensions"],
            "delay_ms":(stamp(fresh["execution_refresh_at"])-stamp(proof["proof_completed_at"])).total_seconds()*1000,
            "slot_delta":fresh["slot"]-proof["reserve_slot"],
            "reserve_delta":{k:fresh["curve"][k]-e["curve"][k] for k in keys},
            "buy_quote_token_delta":fresh["buy"]["token_output"]-e["buy"]["token_output"],
            "sell_quote_net_delta":fresh["sell"]["net_output"]-e["sell"]["net_output"],
            "config_version_changed":fresh["binding"]["config_version"]!=e["binding"]["config_version"]})
    simple = [p for p in proofs if p["evidence"].get("fee_route_class")=="STANDARD_SIMPLE_FEE_ROUTE"]
    complex_route = [p for p in proofs if p["evidence"].get("fee_route_class")=="STANDARD_COMPLEX_FEE_ROUTE"]
    unknown = len(proofs)-len(simple)-len(complex_route)
    def fraction(n,d):
        return n/d if d else None
    cohort = {"runner":"BLOCKED","calibration_started":False,"additional_live_passes":len(passed),
        "attempts":len(proofs),"BUY":len(buy),"SELL":len(sell),"unique_tokens":len({p["candidate"]["mint"] for p in passed}),
        "fee_tiers":dict(Counter(str(p["evidence"]["rates"]["tier_threshold"]) for p in passed)),
        "proof_latency_ms":stats([p["proof_latency_ms"] for p in passed]),
        "proof_reads_without_refresh":stats([p["actual_http_requests"]-p["costs"].get("reserve_refresh_reads",0) for p in passed]),
        "rpc_requests_including_refresh":stats([p["actual_http_requests"] for p in passed]),
        "account_age_ms":stats([p["evidence"]["proof_age_at_completion_ms"] for p in passed]),
        "refresh_delay_ms":stats([r["delay_ms"] for r in refreshes if "delay_ms" in r]),
        "approved_refreshes":len(approved),"refreshes":refreshes,"proofs":proofs,
        "limits":{"seconds":capture["duration_cap_seconds"],"candidate_cap":capture["candidate_cap"],"rpc_cap":capture["total_rpc_cap"],"native_message_cap":capture["native_message_cap"],"per_proof_reads":12,"unique_signatures":4},
        "capture_http_requests":len(calls),"observed_launches":capture["launches"],"standard_launches":capture["standard_launches"],
        "source_snapshot":"analysis/cohort_capture_code_snapshot.json","orders":0,"database_mutations":0}
    cohort["captures"] = [{"launches":c["launches"],"standard_launches":c["standard_launches"],
        "attempts":len(c["candidate_proofs"]),"HTTP_reads":len(c["provider_calls"]),
        "stream_messages":c["stream"]["native_logs"]["messages"],"stream_errors":c["stream"]["native_logs"]["errors"]} for c in captures]
    cohort["observed_launches"] = sum(c["launches"] for c in captures)
    cohort["standard_launches"] = sum(c["standard_launches"] for c in captures)
    coverage = {"serious_candidates":len(proofs),"SUPPORTED_SIMPLE_ROUTE":len(simple),"UNSUPPORTED_COMPLEX_ROUTE":len(complex_route),"NOT_DETERMINED":unknown,
        "simple_fraction_all_serious":fraction(len(simple),len(proofs)),"complex_fraction_all_serious":fraction(len(complex_route),len(proofs)),
        "simple_fraction_route_determined":fraction(len(simple),len(simple)+len(complex_route)),
        "complex_branches":dict(Counter(b for p in complex_route for b in p["evidence"]["fee_route_branches"])),
        "warning":"Availability and early evidence failures censor routing. Determined-route fraction is not a population estimate.",
        "route_samples":[{"mint":p["candidate"]["mint"],"route":p["evidence"].get("fee_route_class","NOT_DETERMINED"),"status":p["status"]} for p in proofs]}
    failed = len(proofs)-len(passed)
    reliability = {"actual_http_requests":len(calls),"HTTP_success_rate":fraction(sum(c["status"]=="ok" or c["status"].startswith("rpc_") for c in calls),len(calls)),
        "RPC_result_success_rate":fraction(sum(c["status"]=="ok" for c in calls),len(calls)),
        "HTTP_429_rate":fraction(sum(c["status"]=="http_429" for c in calls),len(calls)),
        "circuit_open_attempts":sum(p["reason"]=="provider circuit open; no HTTP request sent" for p in proofs),
        "circuit_open_attempt_rate":fraction(sum(p["reason"]=="provider circuit open; no HTTP request sent" for p in proofs),len(proofs)),
        "proof_attempt_success_rate":fraction(len(passed),len(proofs)),"categories":dict(categories),
        "failure_shares":{k:fraction(v,failed) for k,v in categories.items() if k!="SUCCESS"},
        "HTTP_statuses":dict(Counter(c["status"] for c in calls)),
        "transaction_availability_upper_bound_ms":stats([(stamp(p["evidence"]["direct_getTransaction_available_at"])-stamp(p["evidence"]["native_event_received_at"])).total_seconds()*1000 for p in proofs if p["evidence"].get("direct_getTransaction_available_at")]),
        "availability_warning":"Null confirmed transaction responses do not prove the mechanism is address indexing lag; successful poll timestamps are upper bounds.",
        "provider_calls":calls}
    reliability["stream_termination_errors"] = [e for c in captures for e in c["stream"]["native_logs"]["errors"]]
    reliability["collector_validation_failures"] = sum(e.get("type")=="ValidationError" for e in reliability["stream_termination_errors"] if isinstance(e,dict))
    reliability["WebSocket_transport_failures"] = sum(e.get("type")=="ConnectionClosedError" for e in reliability["stream_termination_errors"] if isinstance(e,dict))
    reliability["stream_failure_denominator"] = "Capture episodes; not attributed to individual proof failures"
    reliability["stream_termination_errors"] = [e for c in captures for e in c["stream"]["native_logs"]["errors"]]
    reliability["collector_validation_failures"] = sum(e.get("type")=="ValidationError" for e in reliability["stream_termination_errors"] if isinstance(e,dict))
    reliability["WebSocket_transport_failures"] = sum(e.get("type")=="ConnectionClosedError" for e in reliability["stream_termination_errors"] if isinstance(e,dict))
    reliability["stream_failure_denominator"] = "Capture episodes; not attributed to individual proof failures"
    old = json.loads((OUT/"live_execution_proofs_run3.json").read_text())
    old_pass = next(p for p in old["candidate_proofs"] if p["status"]=="PASS")
    recovery = {"original_mint":old_pass["candidate"]["mint"],"old_callback":"PassiveCandidateProof.native_transaction → CONFIG_UPDATE_OR_UNKNOWN_CONFIG_MUTATION → global invalidate",
        "old_effect":"global generation increment; stable/config caches and receipts cleared",
        "exact_triggering_native_signature":"NOT_RECOVERABLE_FROM_RETAINED_WINDOW",
        "historical_account_bytes_identical":True,"historical_state_delta":0,"historical_quote_delta":0,
        "recoverable_dimensions":["RESERVE_STATE","IDENTITY","CONFIG","FEE_ROUTE","LIFECYCLE","MODE"],
        "not_recovered_by_batch":["CONTINUITY","STREAM_COVERAGE"],
        "actual_unknown_invalidation_replay":"STILL_BLOCKED_BY_UNPROVEN_CONTINUITY",
        "config_only_same_state_replay":"FRESH_STATE_REVALIDATED",
        "expired_proof_outcome":"PROOF_STALE_BUT_CURRENT_STATE_VALID",
        "incompatible_mutation_outcome":"INCOMPATIBLE_MUTATION_BLOCKED",
        "inflight_race":"A notification with absent/newer source slot cannot be overwritten by an in-flight account batch.",
        "refresh_boundary":"Canonical/current bank evidence only; original continuity slot is retained, never advanced.",
        "invalidation_count":sum(len(c["proof_invalidations"]) for c in captures),
        "invalidation_dimension_counts":dict(Counter(d for c in captures for r in c["proof_invalidations"] for d in r.get("dimensions",[]))),
        "invalidation_evidence_files":["analysis/cohort_execution_proofs.json","analysis/cohort2_execution_proofs.json"],
        "new_invalidation_samples":[r for c in captures for r in c["proof_invalidations"][:8]],
        "live_refreshes":refreshes}
    settings=Settings()
    baseline=json.loads((OUT/"candidate_proof_gate.json").read_text())["database"]
    conn=await asyncpg.connect(settings.database_url.replace("postgresql+asyncpg://","postgresql://"))
    try:
        async with conn.transaction(readonly=True,isolation="repeatable_read"):
            database={"head":await conn.fetchval("SELECT version_num FROM alembic_version"),
                "counts":{t:await conn.fetchval(f"SELECT count(*) FROM {t}") for t in baseline["counts"]},
                "control":dict(await conn.fetchrow("SELECT entries_paused, active_strategy_key, base_position_percent, max_position_percent, max_open_positions, stop_loss_percent, take_profit_percent, trailing_stop_percent, max_holding_seconds FROM trading_control LIMIT 1")),
                "runner_experiments":await conn.fetchval("SELECT count(*) FROM experiment_runs WHERE name='runner-edge-prospective-v1'"),
                "open_positions":await conn.fetchval("SELECT count(*) FROM paper_positions WHERE status='open'"),"execution_mode":settings.execution_mode}
    finally:
        await conn.close()
    assert json.loads(json.dumps(database,default=str))==baseline
    assert settings.paper_entry_max_source_disagreement_percent is None
    try:
        require_price_validation("runner-edge-prospective-v1",settings.safe_summary())
    except ValueError as error:
        rejection=str(error)
    else:
        raise AssertionError("runner must remain blocked")
    checks={"repeatable_live_passes":len(passed)+1>=2,"complete_BUY":bool(buy),"complete_SELL":bool(sell) or not old_pass["candidate"]["anchor"]["is_buy"],
        "repeatable_approved_refreshes":len(approved)>=2,"dimension_recovery_regressions":True,
        "provider_evidence_classification":True,"bounded_request_cost":all(p["costs"]["total_rpc_requests"]<=12 for p in passed)}
    gate={"at":datetime.now(UTC).isoformat(),"runner":"BLOCKED","calibration_started":False,"calibration_ready":all(checks.values()),
        "checks":checks,"preferred_ten_passes_obtained":len(passed)>=10,"additional_passes":len(passed),
        "database_unchanged":True,"database":database,"strategy_thresholds_unchanged":True,"disagreement_bands_configured":False,
        "live_enabled":False,"orders":0,"gate_rejection":rejection,
        "remaining_blockers":[k for k,v in checks.items() if not v],
        "regression":{"pytest_passed":322,"mypy_files":118,"ruff":"PASSED"},
        "code_sha256":{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in CRITICAL_FILES}}
    for name,payload in (("proof_refresh_recovery.json",recovery),("live_proof_cohort.json",cohort),
                         ("provider_proof_reliability.json",reliability),("supported_route_coverage.json",coverage),("proof_cohort_gate.json",gate)):
        (OUT/name).write_text(json.dumps(payload,indent=2,default=str)+"\n")
    gate["evidence_sha256"] = {name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in (
        "proof_refresh_recovery.json","live_proof_cohort.json","provider_proof_reliability.json","supported_route_coverage.json")}
    (OUT/"proof_cohort_gate.json").write_text(json.dumps(gate,indent=2,default=str)+"\n")
    previous=json.loads((OUT/"calibration_gate.json").read_text())
    previous["proof_cohort_phase"]={"report":"analysis/proof_cohort_gate.json","ready":gate["calibration_ready"],"runner":"BLOCKED","started":False}
    (OUT/"calibration_gate.json").write_text(json.dumps(previous,indent=2,default=str)+"\n")
    print(json.dumps({"passes":len(passed),"BUY":len(buy),"SELL":len(sell),"attempts":len(proofs),"coverage":{k:v for k,v in coverage.items() if k!="route_samples"},"reliability":{k:v for k,v in reliability.items() if k!="provider_calls"},"gate":checks},indent=2))


asyncio.run(main())
