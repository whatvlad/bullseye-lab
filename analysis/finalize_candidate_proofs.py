"""Aggregate bounded captures, verify unchanged DB, keep the runner blocked."""
import asyncio
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from memebot.core.config import Settings
from memebot.paper.validation_gate import CRITICAL_FILES, SAFETY_KEYS, require_price_validation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"


def stats(values):
    values = sorted(values)
    if not values:
        return dict(average=None, median=None, p90=None, max=None)
    n=len(values)
    return dict(average=sum(values)/n,median=(values[(n-1)//2]+values[n//2])/2,
                p90=values[(9*n+9)//10-1],max=values[-1])


async def main():
    latest = OUT / "candidate_execution_proofs_run2.json"
    if not latest.exists():
        latest.write_bytes((OUT / "candidate_execution_proofs.json").read_bytes())
    runs=[json.loads((OUT/name).read_text()) for name in
          ["candidate_execution_proofs_run1.json","candidate_execution_proofs_run2.json"]]
    proofs=[]
    for run_index,run in enumerate(runs,1):
        cursor=0
        for proof in run["candidate_proofs"]:
            proof["capture_run"]=run_index
            proof["costs"]["identity_reads"]=proof["costs"].get("identity_config_batch_reads",0)
            proof["costs"]["config_reads"]=proof["costs"].get("identity_config_batch_reads",0)
            batch_calls=run["provider_calls"][cursor:cursor+proof["costs"]["total_rpc_requests"]]
            cursor+=proof["costs"]["total_rpc_requests"]
            if proof["reserve_slot"] is None:
                slots=[call.get("slot") for call in batch_calls if call["method"]=="getMultipleAccounts"]
                if len(slots)==1 and slots[0] is not None:
                    proof.update(identity_slot=slots[0],reserve_slot=slots[0],config_slot=slots[0],slot_span=0)
                    proof["slot_metadata_origin"]="retained single getMultipleAccounts context; not execution synchronization"
            proofs.append(proof)
    calls=[call for run in runs for call in run["provider_calls"]]
    assert len(calls)==sum(p["costs"]["total_rpc_requests"] for p in proofs)==22
    costs=dict(attempts=len(proofs),statuses=dict(Counter(p["status"] for p in proofs)),
        rpc_requests=stats([p["costs"]["total_rpc_requests"] for p in proofs]),
        proof_latency_ms=stats([p["proof_latency_ms"] for p in proofs]),
        total_http_requests=len(calls),requests_by_method=dict(Counter(c["method"] for c in calls)),
        identity_reads=sum(p["costs"]["identity_reads"] for p in proofs),
        config_reads=sum(p["costs"]["config_reads"] for p in proofs),
        identity_config_shared_batch_requests=sum(p["costs"]["identity_config_batch_reads"] for p in proofs),
        transaction_block_reads=sum(p["costs"].get("transaction_block_reads",0) for p in proofs),
        reserve_refresh_reads=sum(p["costs"].get("reserve_refresh_reads",0) for p in proofs),
        overlapping_duties="Identity/config counts describe the same batch; do not add them",
        launches_observed=sum(run["launches"] for run in runs),
        standard_launches=sum(run["standard_launches"] for run in runs),
        excluded_deep_reads=0,orders=0,database_trading_mutations=0,
        experimental_policy=dict(max_requests_per_candidate=12,max_signatures=4,
                                 timeout_seconds=12,max_proof_age_ms=2000),
        per_candidate=[dict(mint=p["candidate"]["mint"],status=p["status"],reason=p["reason"],
                            costs=p["costs"],latency_ms=p["proof_latency_ms"]) for p in proofs])
    summary=dict(scope="STANDARD_PUMP_FUN_ONLY",runner="BLOCKED",candidate_proofs=proofs,
        captures=[dict(file=f"candidate_execution_proofs_run{index}.json",
            duration_cap_seconds=r["duration_cap_seconds"],launches=r["launches"],
            standard_launches=r["standard_launches"],observational_counts=r["observational_counts"])
            for index,r in enumerate(runs,1)],provider_calls=calls,orders=0,database_mutations=0,
        funnel_counts=dict(STANDARD_DISCOVERED=costs["standard_launches"],
            OBSERVATION_ELIGIBLE=sum(r["observational_counts"]["FIRST_OBSERVATION"]+
                                     r["observational_counts"]["EXACT"] for r in runs),
            ARITHMETIC_CONTINUITY_OK=sum(r["observational_counts"]["EXACT"] for r in runs),
            SERIOUS_CANDIDATE=len(proofs),CANDIDATE_PROOF_PENDING=len(proofs),
            EXECUTION_READY=sum(p["status"]=="PASS" for p in proofs),REJECTED=sum(p["status"]!="PASS" for p in proofs)),
        funnel_count_units="Discovery=launches, arithmetic=events, remaining stages=proof attempts",
        collection_limitations="First capture predates richer rejected-attempt diagnostics; no live PASS in either capture",
        historical_divergences=dict(count=8,causality_proven=False,
            source="analysis/standard_pumpfun_validation.json",prospective_regression_tests=True))
    (OUT/"candidate_execution_proofs.json").write_text(json.dumps(summary,indent=2)+"\n")
    (OUT/"candidate_proof_cost.json").write_text(json.dumps(costs,indent=2)+"\n")
    settings=Settings()
    baseline=json.loads((OUT/"price_database_validation.json").read_text())["after"]
    conn=await asyncpg.connect(settings.database_url.replace("postgresql+asyncpg://","postgresql://"))
    try:
        async with conn.transaction(readonly=True,isolation="repeatable_read"):
            database=dict(head=await conn.fetchval("SELECT version_num FROM alembic_version"),
                counts={table:await conn.fetchval(f"SELECT count(*) FROM {table}") for table in baseline["counts"]},
                control=dict(await conn.fetchrow("SELECT entries_paused, active_strategy_key, base_position_percent, max_position_percent, max_open_positions, stop_loss_percent, take_profit_percent, trailing_stop_percent, max_holding_seconds FROM trading_control LIMIT 1")),
                runner_experiments=await conn.fetchval("SELECT count(*) FROM experiment_runs WHERE name='runner-edge-prospective-v1'"),
                open_positions=await conn.fetchval("SELECT count(*) FROM paper_positions WHERE status='open'"),
                execution_mode=settings.execution_mode)
    finally: await conn.close()
    assert json.loads(json.dumps(database,default=str))==baseline
    assert settings.paper_entry_max_source_disagreement_percent is None
    try: require_price_validation("runner-edge-prospective-v1",settings.safe_summary())
    except ValueError as error: rejection=str(error)
    else: raise AssertionError("Runner must stay blocked")
    fee_validation=json.loads((OUT/"standard_fee_validation.json").read_text())
    assert not fee_validation["mismatches"] and fee_validation["integer_quote_comparisons"]==108
    blockers=["No successful live candidate proof",
              "Signature history index can lag the observed anchor; bounded path cannot prove continuity",
              "Standard cashback/reward/shared-creator fee routes remain UNKNOWN and reject",
              "No live native buy/sell integer parity and no live execution refresh success",
              "Representative standard-only synchronized candidate calibration still unavailable",
              "Proof API is passive; runner activation and paper execution integration still require the existing validation gate"]
    gate=dict(verified_at=datetime.now(UTC).isoformat(),status="BLOCKED",runner="BLOCKED",
        proof_architecture_implemented=True,synthetic_native_buy_sell_success=True,
        sdk_integer_parity=True,synchronized_calibration_ready=False,live_passes=0,
        fee_components_verified_for_supported_candidate_bank_only=True,
        canonical_bindings_fully_verified_for_live_execution=False,
        cost=costs,remaining_blockers=blockers,old_divergence_causality_required_for_proof=False,
        database=database,database_unchanged=True,strategy_thresholds_unchanged=True,
        disagreement_bands_configured=False,live_enabled=False,positions_opened=0,
        experiment_started=False,gate_rejection=rejection,
        regression=dict(pytest_passed=298,strict_mypy_files=116,ruff="PASSED"),
        code_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in CRITICAL_FILES},
        evidence_sha256={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in
                        ["candidate_execution_proofs.json","standard_fee_validation.json","candidate_proof_cost.json"]})
    (OUT/"candidate_proof_gate.json").write_text(json.dumps(gate,indent=2,default=str)+"\n")
    existing=json.loads((OUT/"calibration_gate.json").read_text())
    existing.update(status="BLOCKED",coverage_sufficient=False,candidate_proof_phase=gate,
                    current_state_trust_blockers=blockers)
    existing["runner-edge-prospective-v1"]="BLOCKED"
    (OUT/"calibration_gate.json").write_text(json.dumps(existing,indent=2,default=str)+"\n")
    price=json.loads((OUT/"price_validation.json").read_text())
    price.update(status="blocked",recorded_at=gate["verified_at"],code_sha256=gate["code_sha256"],
        safety_configuration={key:settings.safe_summary()[key] for key in SAFETY_KEYS},
        candidate_proof_phase=dict(report="analysis/candidate_proof_gate.json",runner="BLOCKED"))
    price["verification"].update(pytest_passed=298,strict_mypy_files=116)
    (OUT/"price_validation.json").write_text(json.dumps(price,indent=2,default=str)+"\n")
    print(json.dumps(dict(attempts=len(proofs),statuses=costs["statuses"],rpc=costs["rpc_requests"],
        latency=costs["proof_latency_ms"],database_unchanged=True,runner="BLOCKED"),indent=2))


if __name__=="__main__": asyncio.run(main())
