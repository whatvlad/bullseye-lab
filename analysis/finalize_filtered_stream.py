"""Report measured filtered pilot separately from failed transport setup trial."""
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from memebot.core.config import Settings
from memebot.paper.validation_gate import CRITICAL_FILES, require_price_validation

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / "analysis/filtered_stream_pilot.json").read_text())
trial = json.loads((ROOT / "analysis/filter_setup_trial_filtered_stream_pilot.json").read_text())
pairs = report["pairs"]
metrics = report["transport"]["metrics"]
duration = report["elapsed_seconds"]
discovery_end = next(g["at"] for g in report["coverage"]["gaps"] if g["reason"] == "DISCOVERY_CAPTURE_CAP")
discovery_duration = (datetime.fromisoformat(discovery_end) - datetime.fromisoformat(report["started_at"])).total_seconds()


def failure_class(proof):
    reason = proof["reason"] or ""
    if reason == "direct anchor transaction unavailable":
        return "FAIL_TRANSACTION_AVAILABILITY"
    if "reconstruction" in reason:
        return "FAIL_RECONSTRUCTION"
    if proof["status"] == "FAIL_STATE_SYNC":
        return "FAIL_SYNC"
    if reason == "successor boundary not reached":
        return "FAIL_HISTORY_WINDOW"
    return proof["status"]


arms = {}
for arm in ("OLD", "NEW"):
    proofs = [p[arm] for p in pairs]
    rpc = sum(p["costs"].get("total_rpc_requests", 0) for p in proofs)
    arms[arm] = {"candidates": len(proofs), "rpc_reads": rpc,
                 "rpc_per_candidate": rpc / len(proofs),
                 "passes": sum(p["status"] == "PASS" for p in proofs),
                 "failure_classes": dict(Counter(failure_class(p) for p in proofs))}
tx_bytes = metrics["transaction_bytes"]
account_bytes = metrics["account_bytes"]
other_bytes = sum(v for k, v in metrics.items() if k.endswith("_bytes")) - tx_bytes - account_bytes
bandwidth = {
    "byte_model": "UTF-8 JSON discovery; protobuf application payload for Geyser; wire/compression/billed bytes unknown",
    "global_discovery_bytes": report["meter"]["decoded_application_bytes"],
    "full_transaction_stream_bytes": tx_bytes, "account_stream_bytes": account_bytes,
    "slot_control_bytes": other_bytes,
    "full_stream_elapsed_seconds_including_drain": duration,
    "discovery_elapsed_seconds_until_capture_cap": discovery_duration,
    "global_discovery_MB_per_hour": report["meter"]["decoded_application_bytes"] / 1e6 * 3600 / discovery_duration,
    "full_transaction_MB_per_hour": tx_bytes / 1e6 * 3600 / duration,
    "account_MB_per_hour": account_bytes / 1e6 * 3600 / duration,
    "total_filtered_stream_MB_per_hour": (tx_bytes + account_bytes + other_bytes) / 1e6 * 3600 / duration,
    "full_transaction_bytes_per_watched_market": tx_bytes / report["watched_markets"],
    "full_transaction_bytes_per_serious_candidate": tx_bytes / len(pairs),
    "bytes_per_successful_proof": None,
    "note": "Ratios of this actual pilot only; not a forecast or prior global-log extrapolation",
}
raw_packets = [json.loads(line) for line in (ROOT / "analysis/filtered_stream_packets.jsonl").read_text().splitlines()]
raw_signatures = {p["signature"] for p in raw_packets}
local_diagnostics = []
for pair in pairs:
    at = datetime.fromisoformat(pair["NEW"]["candidate"]["detected_at"])
    revisions = [r for r in report["transport"]["filter_history"] if datetime.fromisoformat(r["at"]) <= at]
    active = revisions[-1]["accounts"] if revisions else []
    local_diagnostics.append({"mint": pair["mint"], "watch_active_at_candidate": pair["mint"] in active,
        "retained_packet_any_time_in_archive": pair["signature"] in raw_signatures,
        "local_before_proof": pair["local_before_stream_proof"]})
try:
    require_price_validation("runner-edge-prospective-v1", Settings().model_dump(mode="json"))
    runner_blocked = False
except ValueError:
    runner_blocked = True
summary = {
    "status": "WORKING_STREAM_PARTIAL_ACQUISITION_IMPROVEMENT_NOT_VALIDATED_FOR_CALIBRATION",
    "provider": "Alchemy Yellowstone mainnet, user-enabled PAYG, X-Token",
    "runner": "BLOCKED", "runner_gate_rejection_verified": runner_blocked,
    "calibration_started": False, "orders": 0,
    "full_packets_received": metrics["full_packets"], "usable_packets": metrics["usable_packets"],
    "decoder_rejected_packets": metrics["malformed_packets"],
    "archived_normalized_packets": len(raw_packets),
    "complete_provider_archival_for_pilot": False,
    "decoder_rejection_cause": "Not retained during this capture; exact cause cannot be proven. Post-capture raw protobuf retention and reason labels added and tested.",
    "serious_candidates": len(pairs), "locally_available_anchors_before_proof": report["local_evidence_before_proof"],
    "complete_local_history_windows": 0, "arms": arms,
    "live_BUY_PASS": False, "repeatable_live_SELL_PASS": False,
    "paired_rpc_reads": report["rpc_reads"], "setup_trial_rpc_reads": trial["rpc_reads"],
    "task_rpc_reads": report["rpc_reads"] + trial["rpc_reads"], "task_rpc_cap": 96,
    "rpc_reduction_pct": 100 * (arms["OLD"]["rpc_reads"] - arms["NEW"]["rpc_reads"]) / arms["OLD"]["rpc_reads"],
    "bandwidth": bandwidth, "coverage": report["coverage"], "local_diagnostics": local_diagnostics,
    "history_fences_removable": False, "synchronized_calibration_justified": False,
    "capture_vs_final_code": "Pilot preceded raw-protobuf archival/rejection labels, failed-candidate watch release and configurable lower RPC cap; these post-capture improvements were tested, not live re-piloted.",
    "tests": {"passed": 358, "ruff": "PASS", "mypy_source_files": 128},
    "code_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in CRITICAL_FILES},
}
(ROOT / "analysis/filtered_stream_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
gate = {"status": "BLOCKED", "runner-edge-prospective-v1": "BLOCKED", "calibration": "BLOCKED",
        "working_stream": True, "complete_for_window": False, "all_success_criteria_met": False,
        "blockers": ["Only 7 serious paired candidates before unchanged message cap, below 10–20 target",
            "Only 3/7 local anchors; two availability failures in each arm",
            "98 decoder rejections lacked raw archival during this capture",
            "One out-of-order transaction and five per-market overflows",
            "No live BUY PASS or repeatable SELL PASS",
            "Integer fee/curve mismatch, physical reconstruction, same-slot order and history boundary failures remain",
            "No closed-window delivery certificate; four fences and atomic refresh still mandatory"],
        "summary": "analysis/filtered_stream_summary.json", "code_sha256": summary["code_sha256"]}
(ROOT / "analysis/filtered_stream_proof_gate.json").write_text(json.dumps(gate, indent=2) + "\n")
calibration_path = ROOT / "analysis/calibration_gate.json"
calibration = json.loads(calibration_path.read_text())
calibration["filtered_stream_phase"] = {"provider_access_working": True, "ready": False,
    "runner": "BLOCKED", "summary": "analysis/filtered_stream_summary.json"}
calibration_path.write_text(json.dumps(calibration, indent=2) + "\n")
print(json.dumps({"full_packets": metrics["full_packets"], "usable_packets": metrics["usable_packets"],
    "serious_candidates": len(pairs), "local_anchors": report["local_evidence_before_proof"],
    "arms": arms, "bandwidth": bandwidth, "runner_blocked": runner_blocked,
    "task_rpc_reads": summary["task_rpc_reads"], "local_diagnostics": local_diagnostics}, indent=2))
