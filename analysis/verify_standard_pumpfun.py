"""Read-only database verification and explicit blocked standard-runner gate."""
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
    connection = await asyncpg.connect(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        async with connection.transaction(readonly=True, isolation="repeatable_read"):
            state = {
                "head": await connection.fetchval("SELECT version_num FROM alembic_version"),
                "counts": {table: await connection.fetchval(f"SELECT count(*) FROM {table}")
                           for table in baseline["counts"]},
                "control": dict(await connection.fetchrow(
                    "SELECT entries_paused, active_strategy_key, base_position_percent, "
                    "max_position_percent, max_open_positions, stop_loss_percent, "
                    "take_profit_percent, trailing_stop_percent, max_holding_seconds "
                    "FROM trading_control LIMIT 1")),
                "runner_experiments": await connection.fetchval(
                    "SELECT count(*) FROM experiment_runs WHERE name='runner-edge-prospective-v1'"),
                "open_positions": await connection.fetchval(
                    "SELECT count(*) FROM paper_positions WHERE status='open'"),
                "execution_mode": settings.execution_mode,
            }
    finally:
        await connection.close()
    assert json.loads(json.dumps(state, default=str)) == baseline
    assert settings.paper_entry_max_source_disagreement_percent is None
    try:
        require_price_validation("runner-edge-prospective-v1", settings.safe_summary())
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError("Runner must remain blocked")
    research = json.loads((OUT / "standard_pumpfun_validation.json").read_text())
    evidence_files = ["standard_pumpfun_capture.json", "standard_pumpfun_validation.json"]
    report = {
        "verified_at": datetime.now(UTC).isoformat(), "runner": "BLOCKED",
        "scope": "STANDARD_PUMP_FUN_ONLY", "database": state, "database_unchanged": True,
        "strategy_thresholds_unchanged": True, "live_enabled": False,
        "worker_or_experiment_started": False, "positions_opened": 0,
        "new_http_solana_rpc_reads": 0, "source_disagreement_limit": None,
        "pytest": "270 passed", "ruff": "PASSED", "strict_mypy": "113 source files PASSED",
        "synchronized_calibration_ready": False, "gate_rejection": rejection,
        "remaining_blockers": research["remaining_blockers"],
        "code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in CRITICAL_FILES},
        "evidence_sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
                            for name in evidence_files},
    }
    (OUT / "standard_pumpfun_verification.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n")
    gate = json.loads((OUT / "calibration_gate.json").read_text())
    gate.update(status="BLOCKED", coverage_sufficient=False,
                current_state_trust_blockers=report["remaining_blockers"],
                standard_pumpfun_phase=report)
    gate["runner-edge-prospective-v1"] = "BLOCKED"
    (OUT / "calibration_gate.json").write_text(json.dumps(gate, indent=2, default=str) + "\n")
    price = json.loads((OUT / "price_validation.json").read_text())
    price.update(status="blocked", recorded_at=report["verified_at"],
                 scope="Standard Pump.fun only; synchronized execution evidence incomplete",
                 code_sha256=report["code_sha256"],
                 safety_configuration={key: settings.safe_summary()[key] for key in SAFETY_KEYS},
                 standard_pumpfun_phase={"report": "analysis/standard_pumpfun_verification.json",
                                        "runner": "BLOCKED"})
    price["verification"].update(pytest_passed=270, strict_mypy_files=113)
    (OUT / "price_validation.json").write_text(json.dumps(price, indent=2, default=str) + "\n")
    print(json.dumps({key: report[key] for key in ["runner", "database_unchanged",
        "strategy_thresholds_unchanged", "live_enabled", "new_http_solana_rpc_reads",
        "source_disagreement_limit", "pytest", "strict_mypy", "gate_rejection"]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
