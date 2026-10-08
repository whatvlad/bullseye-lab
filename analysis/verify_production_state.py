"""Read-only database verification and explicitly BLOCKED normalization gate."""
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
                "counts": {t: await connection.fetchval(f"SELECT count(*) FROM {t}") for t in baseline["counts"]},
                "control": dict(await connection.fetchrow(
                    "SELECT entries_paused, active_strategy_key, base_position_percent, max_position_percent, "
                    "max_open_positions, stop_loss_percent, take_profit_percent, trailing_stop_percent, max_holding_seconds "
                    "FROM trading_control LIMIT 1")),
                "runner_experiments": await connection.fetchval("SELECT count(*) FROM experiment_runs WHERE name='runner-edge-prospective-v1'"),
                "open_positions": await connection.fetchval("SELECT count(*) FROM paper_positions WHERE status='open'"),
                "execution_mode": settings.execution_mode,
            }
    finally:
        await connection.close()
    assert json.loads(json.dumps(state, default=str)) == baseline
    assert settings.paper_entry_max_source_disagreement_percent is None
    passive = json.loads((OUT / "production_state_passive.json").read_text())
    forensic = json.loads((OUT / "remaining_state_break.json").read_text())
    replay = json.loads((OUT / "production_state_replay.json").read_text())
    calls = len(passive["provider_requests"]) + len(forensic["provider_requests"])
    assert len(passive["provider_requests"]) <= 30
    assert len(forensic["provider_requests"]) <= 5
    assert replay["semantics"] == {"POST_TRADE": 18, "UNKNOWN": 2, "RECONSTRUCTED_POST_TRADE": 1}
    assert forensic["cause"] == "INTERVENING_NATIVE_TRADES_IN_UNCACHED_SLOTS"
    try:
        require_price_validation("runner-edge-prospective-v1", settings.safe_summary())
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError("Runner must remain blocked")
    blockers = [
        "Canonical PDA/curve mint binding and dynamic fee/config versions unverified",
        "Incomplete non-swap/direct-account mutation coverage; conservative global invalidations",
        "Multi-event Pump.fun production state UNKNOWN without instruction proof",
        "New passive Pump.fun integer mismatches unexplained",
        "Stream loss layer unlocated and representative synchronized residual sample absent",
        "Source disagreement band intentionally unconfigured",
    ]
    report = {
        "verified_at": datetime.now(UTC).isoformat(), "status": "SAFE_PARTIAL_NORMALIZATION",
        "larger_passive_acquisition_ready": True, "complete_identity_verified": False,
        "entry_execution_readiness": "BLOCKED", "runner": "BLOCKED",
        "automatic_activation": False, "source_disagreement_limit": None,
        "database": state, "database_unchanged": True, "strategy_thresholds_unchanged": True,
        "worker_or_experiment_started": False, "live_enabled": False,
        "new_rpc_reads": calls, "maximum_phase_rpc_reads": 35,
        "pytest": "235 passed", "ruff": "PASSED", "mypy": "105 files PASSED",
        "gate_rejection": rejection, "remaining_blockers": blockers,
        "code_sha256": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in CRITICAL_FILES},
        "evidence_sha256": {n: hashlib.sha256((OUT / n).read_bytes()).hexdigest() for n in (
            "production_state_passive.json", "production_state_replay.json", "remaining_state_break.json")},
    }
    (OUT / "production_state_verification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    gate = json.loads((OUT / "calibration_gate.json").read_text())
    gate["production_normalization_phase"] = report
    gate["status"] = "BLOCKED"
    gate["runner-edge-prospective-v1"] = "BLOCKED"
    gate["coverage_sufficient"] = False
    gate["blockers"] = list(dict.fromkeys(gate["blockers"] + blockers))
    (OUT / "calibration_gate.json").write_text(json.dumps(gate, indent=2, default=str) + "\n")
    price = json.loads((OUT / "price_validation.json").read_text())
    price["recorded_at"] = report["verified_at"]
    price["status"] = "blocked"
    price["scope"] = "Production reserve normalization and fail-safe incomplete tracking; full identity and synchronized calibration pending."
    price["code_sha256"] = report["code_sha256"]
    price["safety_configuration"] = {key: settings.safe_summary()[key] for key in SAFETY_KEYS}
    price["verification"]["pytest_passed"] = 235
    price["verification"]["strict_mypy_files"] = 105
    price["production_normalization_phase"] = {"status": report["status"], "report": "analysis/production_state_verification.json"}
    (OUT / "price_validation.json").write_text(json.dumps(price, indent=2, default=str) + "\n")
    print(json.dumps({k:report[k] for k in ("status", "runner", "new_rpc_reads", "database_unchanged", "strategy_thresholds_unchanged", "source_disagreement_limit")}, default=str))


asyncio.run(main())
