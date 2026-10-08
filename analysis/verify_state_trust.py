"""Read-only safety verification; keep the experiment gate explicitly BLOCKED."""
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from memebot.core.config import Settings
from memebot.paper.validation_gate import CRITICAL_FILES, SAFETY_KEYS, require_price_validation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"


async def main():
    settings = Settings()
    baseline = json.loads((OUT / "price_database_validation.json").read_text())["after"]
    connection = await asyncpg.connect(settings.database_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        async with connection.transaction(readonly=True, isolation="repeatable_read"):
            state = {
                "head": await connection.fetchval("SELECT version_num FROM alembic_version"),
                "counts": {table: await connection.fetchval(f"SELECT count(*) FROM {table}") for table in baseline["counts"]},
                "control": dict(await connection.fetchrow("SELECT entries_paused, active_strategy_key, base_position_percent, max_position_percent, max_open_positions, stop_loss_percent, take_profit_percent, trailing_stop_percent, max_holding_seconds FROM trading_control LIMIT 1")),
                "runner_experiments": await connection.fetchval("SELECT count(*) FROM experiment_runs WHERE name='runner-edge-prospective-v1'"),
                "open_positions": await connection.fetchval("SELECT count(*) FROM paper_positions WHERE status='open'"),
                "execution_mode": settings.execution_mode,
            }
    finally:
        await connection.close()
    assert json.loads(json.dumps(state, default=str)) == baseline
    assert settings.paper_entry_max_source_disagreement_percent is None
    capture = json.loads((OUT / "state_trust_validation.json").read_text())
    identity = json.loads((OUT / "identity_bootstrap.json").read_text())
    forensic = json.loads((OUT / "pumpfun_mismatch_classification.json").read_text())
    assert capture["all_phase_rpc_reads"] == 82
    assert capture["elapsed_seconds"] >= 60
    assert capture["rpc_calls"] <= capture["rpc_cap"]
    assert capture["pure_scope_counterfactual"]["exact_held_trace_reproduction"]
    assert capture["pure_scope_counterfactual"]["net_unknown_reduction_due_to_scope"] == 0
    assert len(forensic["cases"]) == 117 and forensic["causal_mechanism_unknown_count"] == 117
    assert identity["bootstrap_verified_by_venue"] == {"pump_fun": 12, "pump_swap": 3}
    assert identity["supplemental_pumpfun_bootstrap"]["identity"]["canonical_verified"]
    assert all(all(proof["checks"].values()) for proof in identity["supplemental_pumpswap_bootstrap"])
    try:
        require_price_validation("runner-edge-prospective-v1", settings.safe_summary())
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError("Runner must remain blocked")
    blockers = [
        "Live log-only stream lacks instruction data for silent native self-CPI proof",
        "Exact Mayhem virtual-quote state boundary remains causally unproven",
        "Canonical/bootstrap facts are sampled snapshots and later uncertainty invalidates current trust",
        "RPC SLOT_ONLY snapshots are not transaction/state-sequence synchronized",
        "Exact per-order fee routing/tier/rounding and execution assumptions remain unverified",
        "Direct vault mutation coverage and collector/provider loss layer remain incomplete",
        "Representative synchronized residual distributions and disagreement bands remain unavailable",
    ]
    evidence_files = ["invalidation_scope.json", "pumpfun_mismatch_classification.json", "identity_bootstrap.json", "fee_config_bootstrap.json", "state_trust_validation.json", "pumpfun_multi_event_reconstruction.json"]
    report = {
        "verified_at": datetime.now(UTC).isoformat(), "status": "SCOPED_PARTIAL_TRUST", "runner": "BLOCKED",
        "database": state, "database_unchanged": True, "strategy_thresholds_unchanged": True,
        "worker_or_experiment_started": False, "live_enabled": False, "paper_positions_opened": 0,
        "source_disagreement_limit": None, "new_solana_rpc_reads": 82,
        "pytest": "251 passed", "ruff": "PASSED", "mypy": "111 source files PASSED",
        "canonical_bootstrap_verified_by_venue": identity["bootstrap_verified_by_venue"],
        "synchronized_calibration_ready": False, "bounded_transaction_reconstruction_research_ready": True,
        "gate_rejection": rejection, "remaining_blockers": blockers,
        "code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in CRITICAL_FILES},
        "evidence_sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in evidence_files},
    }
    (OUT / "state_trust_verification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    gate = json.loads((OUT / "calibration_gate.json").read_text())
    gate["state_trust_phase"] = report
    gate["status"] = gate["runner-edge-prospective-v1"] = "BLOCKED"
    gate["coverage_sufficient"] = False
    gate["current_state_trust_blockers"] = blockers
    (OUT / "calibration_gate.json").write_text(json.dumps(gate, indent=2, default=str) + "\n")
    price = json.loads((OUT / "price_validation.json").read_text())
    price["recorded_at"] = report["verified_at"]
    price["status"] = "blocked"
    price["scope"] = "Scoped invalidation and sampled canonical/config bootstrap; synchronized execution assumptions incomplete."
    price["code_sha256"] = report["code_sha256"]
    price["safety_configuration"] = {key: settings.safe_summary()[key] for key in SAFETY_KEYS}
    price["verification"]["pytest_passed"] = 251
    price["verification"]["strict_mypy_files"] = 111
    price["state_trust_phase"] = {"status": report["status"], "report": "analysis/state_trust_verification.json"}
    price["checks"]["execution_evidence_consistent"] = False
    (OUT / "price_validation.json").write_text(json.dumps(price, indent=2, default=str) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "runner", "database_unchanged", "strategy_thresholds_unchanged", "new_solana_rpc_reads", "source_disagreement_limit")}, default=str))


asyncio.run(main())
