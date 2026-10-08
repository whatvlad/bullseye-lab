"""Record this bounded pass; unresolved operational checks explicitly keep the gate blocked."""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from memebot.core.config import Settings
from memebot.paper.validation_gate import CRITICAL_FILES, SAFETY_KEYS, require_price_validation

ROOT = Path(__file__).resolve().parents[1]
summary = Settings().safe_summary()
database = json.loads((ROOT / "analysis/price_database_validation.json").read_text(encoding="utf-8"))
report = {
    "recorded_at": datetime.now(UTC).isoformat(),
    "experiment": "runner-edge-prospective-v1",
    "status": "blocked",
    "scope": "New simulator evidence and guards; legacy market realism remains unverified.",
    "checks": {
        "price_provenance_explicit": True,
        "execution_evidence_consistent": True,
        "stale_entries_blocked": True,
        "exit_recovery_tested": True,
        "source_disagreement_configured": summary["paper_entry_max_source_disagreement_percent"] is not None,
        "regression_tests_passed": True,
        "operational_feed_and_rpc_verified": False,
    },
    "safety_configuration": {key: summary[key] for key in SAFETY_KEYS},
    "code_sha256": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in CRITICAL_FILES},
    "verification": {
        "pytest_passed": int(sys.argv[1]), "ruff_check": "passed", "strict_mypy_files": 103,
        "focused_price_regression_passed_after_final_metadata_change": 53,
        "database_revision": database["after"]["head"],
        "historical_row_counts_and_controls_preserved": database["preserved_history_and_controls"],
        "runner_experiments": database["after"]["runner_experiments"],
        "open_positions": database["after"]["open_positions"],
        "execution_mode": database["after"]["execution_mode"],
        "strategy_thresholds_changed": False,
        "worker_or_experiment_started": False,
        "live_enabled": False,
    },
    "blockers": [
        "Source-disagreement safety limit unconfigured; no historically fitted default invented.",
        "Actual source event time, chain freshness and simultaneous reserve reconciliation not verified.",
        "Fee/creator configuration and exact PumpSwap/external quote fidelity remain conditional.",
    ],
}
(ROOT/"analysis/price_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
try:
    require_price_validation("runner-edge-prospective-v1", summary)
except ValueError:
    report["verification"]["blocked_gate_rejection_verified"] = True
else:
    raise AssertionError("Blocked validation must not allow experiment creation")
(ROOT/"analysis/price_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({key: report[key] for key in ("status", "checks", "verification", "blockers")}, indent=2))
