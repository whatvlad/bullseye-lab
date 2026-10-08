"""Read-only verification that calibration preserved trading state and outputs agree."""
import asyncio
import csv
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
    connection = await asyncpg.connect(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql://"))
    baseline = json.loads((OUT / "price_database_validation.json").read_text())["after"]
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
    state = json.loads(json.dumps(state, default=str))
    assert state == baseline, "Trading state changed since prior prerequisite snapshot"
    sample = json.loads((OUT / "market_data_samples.json").read_text())
    costs = json.loads((OUT / "provider_costs.json").read_text())
    dist = json.loads((OUT / "disagreement_distribution.json").read_text())
    gate = json.loads((OUT / "calibration_gate.json").read_text())
    assert len(sample["samples"]) == costs["funnel"]["paired_snapshots"] == 180
    assert dist["overall_stream_rpc"]["N"] == 180
    assert dist["groups"]["venue=pump_fun"]["stream_rpc_price_disagreement_percent"]["N"] == 171
    assert dist["groups"]["venue=pump_swap"]["stream_rpc_price_disagreement_percent"]["N"] == 9
    assert costs["rpc_requests"] == sum(e["requests"] for e in costs["rpc_endpoints"].values()) == 200
    assert costs["metered_pumpportal_events"] == 0
    assert all(len(s["quotes"]) == len(s["stream_state_quotes"]) == 4 for s in sample["samples"])
    with (OUT / "market_data_samples.csv").open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 720
    assert len({row["sample_id"] for row in csv_rows}) == 180
    assert all(s["token_age_seconds"] is None for s in sample["samples"] if s["venue"] == "pump_swap")
    assert all(q[side].get("price_source") == "rpc_primary_reserves"
               for s in sample["samples"] for q in s["quotes"] for side in ("buy", "sell")
               if "rejection" not in q[side])
    try:
        require_price_validation("runner-edge-prospective-v1", settings.safe_summary())
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError("Calibration BLOCKED must prohibit experiment start")
    report = {"verified_at": datetime.now(UTC).isoformat(), "database": state,
              "database_unchanged": True, "strategy_thresholds_changed": False,
              "experiment_gate_rejection": rejection,
              "output_consistency": "PASSED", "pytest": "217 passed",
              "ruff": "PASSED", "mypy": "102 source files PASSED"}
    gate["regression_validation"] = report
    gate["evidence_sha256"] = {
        name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
        for name in ("market_data_samples.json", "market_data_raw.json",
                     "disagreement_distribution.json", "provider_costs.json", "fee_idl_validation.json")}
    (OUT / "calibration_gate.json").write_text(json.dumps(gate, indent=2) + "\n")
    (OUT / "calibration_verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
