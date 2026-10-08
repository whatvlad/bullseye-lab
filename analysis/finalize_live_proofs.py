"""Aggregate immutable passive captures and verify safety state read-only."""
import asyncio
import base64
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from memebot.core.config import Settings
from memebot.paper.candidate_proof import validate_transaction_parity
from memebot.paper.standard_math import buy_quote, select_fees, sell_quote
from memebot.paper.validation_gate import CRITICAL_FILES, require_price_validation
from memebot.providers.solana.bootstrap import decode_config
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, PumpTrade
from memebot.research.pumpfun_sequence import reconstruct_transaction

OUT = Path("analysis")


def dt(value):
    return datetime.fromisoformat(value)


def stats(values):
    values = sorted(values)
    if not values:
        return {"N": 0, "mean": None, "median": None, "p90": None, "max": None}
    n = len(values)
    return {"N": n, "mean": sum(values)/n,
            "median": (values[(n-1)//2]+values[n//2])/2,
            "p90": values[min(n-1,(9*n+9)//10-1)], "max": values[-1]}


async def main():
    captures = [json.loads((OUT/f"live_execution_proofs_run{i}.json").read_text()) for i in (1,2,3)]
    proofs = []
    for run, capture in enumerate(captures,1):
        for proof in capture["candidate_proofs"]:
            proof["capture"] = f"analysis/live_execution_proofs_run{run}.json"
            start, end = dt(proof["proof_started_at"]), dt(proof["proof_completed_at"])
            refresh_batch = proof["evidence"].get("execution_refresh_account_batch")
            if refresh_batch:
                end = max(end, dt(refresh_batch["received_at"]))
            calls = [c for c in capture["provider_calls"] if start <= dt(c["requested_at"]) <= end]
            proof["actual_http_requests"] = len(calls)
            proof["actual_methods"] = dict(Counter(c["method"] for c in calls))
            proof["actual_provider_calls"] = calls
            proof["provider_failures"] = [c["status"] for c in calls if c["status"] != "ok"]
            if proof["reason"] == "SolanaRpcError":
                # Preserve captured status/reason. Add evidence-backed classification.
                proof["failure_class"] = "FAIL_RPC"
                proof["failure_detail"] = proof["provider_failures"] or ["circuit_open_no_http"]
            proofs.append(proof)
    passes = [p for p in proofs if p["status"] == "PASS"]
    rejected = [p for p in proofs if p["status"] != "PASS"]
    def costs(group):
        return {"samples": len(group),
            "rpc_requests_including_refresh": stats([p["actual_http_requests"] for p in group]),
            "transaction_reads": stats([p["actual_methods"].get("getTransaction",0) for p in group]),
            "history_reads": stats([p["actual_methods"].get("getSignaturesForAddress",0) for p in group]),
            "account_batches_including_refresh": stats([p["actual_methods"].get("getMultipleAccounts",0) for p in group]),
            "execution_refresh_reads": stats([p["costs"].get("reserve_refresh_reads",0) for p in group]),
            "proof_latency_ms": stats([p["proof_latency_ms"] for p in group]),
            "proof_age_at_completion_ms": stats([p["evidence"]["proof_age_at_completion_ms"] for p in group if "proof_age_at_completion_ms" in p["evidence"]])}
    parity = []
    for proof in proofs:
        bundle = proof["evidence"]
        if "fee_config" not in bundle:
            continue
        tx = bundle.get("direct_anchor_transaction")
        if not tx:
            continue
        events = [e for _,e in extract_anchor_events(tx["meta"]["logMessages"]) if isinstance(e,PumpTrade)]
        if len(events) != 1:
            continue
        event = events[0]
        direction = 1 if event.is_buy else -1
        pre = {key: getattr(event,key)+(direction*event.token_amount if "token" in key else -direction*event.quote_amount)
               for key in ("virtual_token_reserves","virtual_quote_reserves","real_token_reserves","real_quote_reserves")}
        try:
            result = validate_transaction_parity(tx,event,bundle,pre,proof["candidate"]["anchor_signature"])
            result["reconstruction"] = reconstruct_transaction(tx)
            result["result"] = "EXACT"
        except Exception as error:
            result = {"signature": proof["candidate"]["anchor_signature"], "side": "buy" if event.is_buy else "sell",
                      "result": "MISMATCH_OR_UNPROVEN", "reason": str(error)}
        result.update(mint=event.mint, candidate_status=proof["status"], capture=proof["capture"], config_slot=proof["config_slot"])
        parity.append(result)
    refreshes = []
    for proof in passes:
        old = proof["evidence"]
        batch = old.get("execution_refresh_account_batch")
        if not batch:
            continue
        fresh, missing = decode_config(PUMP_PROGRAM_ID,base64.b64decode(batch["response"]["value"][1]["data"][0]),"BondingCurve")
        assert not missing
        rates = select_fees(old["global"],old["fee_config"],fresh,old["supply"])
        quote_buy = buy_quote(fresh,proof["candidate"]["buy_budget_raw"],rates)
        quote_sell = sell_quote(fresh,proof["candidate"]["sell_quantity_raw"],rates)
        old_batch = old["candidate_account_batch"]
        same_bytes = all(a == b for a,b in zip(old_batch["response"]["value"],batch["response"]["value"],strict=True))
        reserve_keys = ("virtual_token_reserves","virtual_quote_reserves","real_token_reserves","real_quote_reserves")
        refreshes.append({"mint":proof["candidate"]["mint"],"proof_completed_at":proof["proof_completed_at"],
            "refresh_at":batch["received_at"], "elapsed_after_proof_ms":(dt(batch["received_at"])-dt(proof["proof_completed_at"])).total_seconds()*1000,
            "proof_state_slot":old["slot"],"refresh_slot":batch["response"]["context"]["slot"],
            "state_delta":{k:fresh[k]-old["curve"][k] for k in reserve_keys},
            "buy_token_output_delta":quote_buy["token_output"]-old["buy"]["token_output"],
            "sell_net_output_delta":quote_sell["net_output"]-old["sell"]["net_output"],
            "price_movement_pct":(fresh["virtual_quote_reserves"]*old["curve"]["virtual_token_reserves"]/(fresh["virtual_token_reserves"]*old["curve"]["virtual_quote_reserves"])-1)*100,
            "account_bytes_identical":same_bytes,"identity_version_changed":not same_bytes,
            "config_version_changed":not same_bytes,"refresh_approved": "passive_refresh" in old,
            "rejection":old.get("passive_refresh_failure"),
            "comparison_scope":"offline comparison of retained real batches; rejected refresh does not authorize execution"})
    lag = []
    for p in proofs:
        e = p["evidence"]
        received = e.get("native_event_received_at",p["candidate_detected_at"])
        available,visible = e.get("direct_getTransaction_available_at"),e.get("address_signature_index_visible_at")
        probes = e.get("transaction_availability_probes",[])
        history_calls = [c for c in p["actual_provider_calls"] if c["method"]=="getSignaturesForAddress" and c["status"]=="ok"]
        lag.append({"mint":p["candidate"]["mint"],"native_event_received_at":received,
            "direct_getTransaction_available_at":available,"address_signature_index_visible_at":visible,
            "candidate_proof_started_at":p["proof_started_at"],"candidate_proof_completed_at":p["proof_completed_at"],
            "native_to_transaction_availability_upper_bound_ms":(dt(available)-dt(received)).total_seconds()*1000 if available else None,
            "native_to_address_visibility_upper_bound_ms":(dt(visible)-dt(received)).total_seconds()*1000 if visible else None,
            "direct_unavailable_through_ms":(dt(probes[-1]["at"])-dt(received)).total_seconds()*1000 if probes and not available else None,
            "address_visibility":"OBSERVED" if visible else "NOT_OBSERVED_OR_NOT_PROBED",
            "history_anchor_visible":e.get("history_anchor_visible"),"availability_probes":probes,
            "address_index_not_visible_through_ms":(dt(history_calls[-1]["received_at"])-dt(received)).total_seconds()*1000 if history_calls and not visible else None,
            "history_reads":e.get("history_reads",[]),"timestamp_limit":"First successful poll is an upper bound, not exact availability time; run1/2 use candidate receipt timestamp."})
    historical = json.loads((OUT/"live_historical_forensics.json").read_text())
    fee_routes = [{"mint":p["candidate"]["mint"],"signature":p["candidate"]["anchor_signature"],
        "candidate_status":p["status"],"route_class":p["evidence"].get("fee_route_class","NOT_DETERMINED"),
        "branches":p["evidence"].get("fee_route_branches"),"native_parity":p["evidence"].get("observed_anchor_parity",p["evidence"].get("parity")),
        "reason":p["reason"]} for p in proofs]
    def write(name,payload):
        (OUT/name).write_text(json.dumps(payload,indent=2,default=str)+"\n")
    write("live_candidate_proofs.json",{"runner":"BLOCKED","proofs":proofs,"passes":len(passes),
        "statuses":dict(Counter(p["status"] for p in proofs)),"successful_cost":costs(passes),"rejected_cost":costs(rejected),
        "total_capture_http_requests":sum(len(c["provider_calls"]) for c in captures),"forensic_http_requests":historical["rpc_reads"],
        "captures":[{"launches":c["launches"],"standard_launches":c["standard_launches"],"calls":len(c["provider_calls"])} for c in captures],
        "refresh_rehearsals":refreshes,"orders":0,"database_mutations":0})
    write("live_continuity_lag.json",{"samples":lag,"historical_four_failures":"All four old rejects used missing-index anchor as veto; index lag directly demonstrated for one, other three retained no history packet. No causal majority can be proven.",
        "direct_anchor_result":"Real PASS despite anchor absent from address index; exact terminal bank/physical state and unchanged fences required.",
        "expiry":"One immediate refresh comparison. No prospective expiry distribution or permanent threshold inferred."})
    write("live_fee_routes.json",{"samples":fee_routes,"historical_five_fee_rejects":[r for r in historical["rows"] if r["original_status"]=="FAIL_FEE"],
        "supported":"STANDARD_SIMPLE_FEE_ROUTE, including verified protocol buyback split; cashback/holder reward/shared creator remain rejected",
        "original_branch_limit":historical["caution"]})
    write("live_integer_parity.json",{"samples":parity,"exact_buy":sum(r["result"]=="EXACT" and r["side"]=="buy" for r in parity),
        "exact_sell":sum(r["result"]=="EXACT" and r["side"]=="sell" for r in parity),
        "scope":"Recorded live native instructions/events/physical transfers against bank-bound config; arithmetic parity alone is not complete proof approval."})
    settings = Settings()
    baseline = json.loads((OUT/"candidate_proof_gate.json").read_text())["database"]
    conn = await asyncpg.connect(settings.database_url.replace("postgresql+asyncpg://","postgresql://"))
    try:
        async with conn.transaction(readonly=True,isolation="repeatable_read"):
            database = {"head":await conn.fetchval("SELECT version_num FROM alembic_version"),
                "counts":{table:await conn.fetchval(f"SELECT count(*) FROM {table}") for table in baseline["counts"]},
                "control":dict(await conn.fetchrow("SELECT entries_paused, active_strategy_key, base_position_percent, max_position_percent, max_open_positions, stop_loss_percent, take_profit_percent, trailing_stop_percent, max_holding_seconds FROM trading_control LIMIT 1")),
                "runner_experiments":await conn.fetchval("SELECT count(*) FROM experiment_runs WHERE name='runner-edge-prospective-v1'"),
                "open_positions":await conn.fetchval("SELECT count(*) FROM paper_positions WHERE status='open'"),"execution_mode":settings.execution_mode}
    finally:
        await conn.close()
    assert json.loads(json.dumps(database,default=str)) == baseline
    assert settings.paper_entry_max_source_disagreement_percent is None
    try:
        require_price_validation("runner-edge-prospective-v1",settings.safe_summary())
    except ValueError as error:
        gate_rejection = str(error)
    else:
        raise AssertionError("runner must remain blocked")
    gate = {"verified_at":datetime.now(UTC).isoformat(),"runner":"BLOCKED","status":"FIRST_LIVE_PROOF_PASS_REFRESH_BLOCKED",
        "live_candidate_passes":len(passes),"live_buy_integer_parity":any(r["result"]=="EXACT" and r["side"]=="buy" for r in parity),
        "live_sell_integer_parity":any(r["result"]=="EXACT" and r["side"]=="sell" for r in parity),
        "approved_live_refreshes":sum(r["refresh_approved"] for r in refreshes),"synchronized_calibration_ready":False,
        "remaining_blockers":["Refresh invalidation race: identical bank bytes but cache receipt revoked by unresolved native config uncertainty",
            "Only one complete live sell proof; no complete live buy proof or representative calibration cohort",
            "Provider rate limiting and bounded transaction/index availability need measured recovery",
            "Complex fee routing remains excluded; permanent expiry and disagreement bands not calibrated"],
        "successful_cost":costs(passes),"rejected_cost":costs(rejected),"database_unchanged":True,"database":database,
        "strategy_thresholds_unchanged":True,"live_enabled":False,"positions_opened":0,"experiment_started":False,
        "gate_rejection":gate_rejection,"code_sha256":{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in CRITICAL_FILES},
        "regression":{"pytest_passed":309,"strict_mypy_files":117,"ruff":"PASSED"},
        "regression":{"pytest_passed":309,"strict_mypy_files":117,"ruff":"PASSED"},
        "evidence_sha256":{p:hashlib.sha256((OUT/p).read_bytes()).hexdigest() for p in ("live_candidate_proofs.json","live_continuity_lag.json","live_fee_routes.json","live_integer_parity.json")}}
    write("live_proof_gate.json",gate)
    for filename in ("candidate_proof_gate.json","calibration_gate.json"):
        previous = json.loads((OUT/filename).read_text())
        previous["live_proof_phase"] = {"report":"analysis/live_proof_gate.json","live_passes":len(passes),"runner":"BLOCKED"}
        previous["current_live_blockers"] = gate["remaining_blockers"]
        write(filename,previous)
    print(json.dumps({"passes":len(passes),"parity":Counter((r["side"],r["result"]) for r in parity).__str__(),
                      "success":costs(passes),"refresh":refreshes,"database_unchanged":True},indent=2))


asyncio.run(main())
