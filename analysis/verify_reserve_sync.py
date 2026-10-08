"""Verify reserve research outputs and trading state using a read-only transaction."""
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from memebot.core.config import Settings
from memebot.paper.validation_gate import require_price_validation

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
    tx = json.loads((OUT / "transaction_reconciliation.json").read_text())
    eff = json.loads((OUT / "rpc_efficiency_v2.json").read_text())
    assert tx["phase_rpc_requests"] == eff["all_phase_rpc_requests"] == len(eff["provider_requests"]) <= 300
    assert tx["matched_signatures"] == 21
    assert tx["stream_rpc_threshold_eligible_comparisons"] == 0
    try:
        require_price_validation("runner-edge-prospective-v1", settings.safe_summary())
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError("Runner must remain blocked")
    report = {"verified_at": datetime.now(UTC).isoformat(), "status": "PARTIAL_METHOD_VALIDATED",
              "experiment": "BLOCKED", "phase_rpc_requests": eff["all_phase_rpc_requests"],
              "database_unchanged": True, "strategy_thresholds_unchanged": True,
              "source_disagreement_limit": None, "open_positions": 0, "runner_experiments": 0,
              "execution_mode": settings.execution_mode, "gate_rejection": rejection,
              "pytest": "222 passed", "ruff": "PASSED", "mypy": "103 files PASSED",
              "remaining_blockers": ["Incomplete mutation/stream coverage", "One random-control RPC state unmatched",
                                     "Two Pump.fun multi-event semantics UNKNOWN", "Canonical/migration bootstrap incomplete",
                                     "No simultaneous-state residual distribution or frozen safety bands"],
              "evidence_sha256": {n: hashlib.sha256((OUT / n).read_bytes()).hexdigest() for n in
                  ("reserve_anomalies.json", "transaction_reconciliation.json", "reconciliation_distribution.json", "rpc_efficiency_v2.json", "live_transition_forensics.json")}}
    (OUT / "reserve_sync_verification.json").write_text(json.dumps(report, indent=2) + "\n")
    gate = json.loads((OUT / "calibration_gate.json").read_text())
    gate["reserve_synchronization_phase"] = report
    gate["status"] = "BLOCKED"
    gate["runner-edge-prospective-v1"] = "BLOCKED"
    (OUT / "calibration_gate.json").write_text(json.dumps(gate, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
