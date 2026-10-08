"""Print safe aggregate fields from the bounded recovery diagnostic."""

import argparse
import json
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--log", default="analysis/operational_recovery_20261005.err.log")
args = parser.parse_args()
path = Path(args.log)
rows = []
for line in path.read_text(encoding="utf-8-sig").splitlines():
    try:
        rows.append(json.loads(line))
    except ValueError:
        pass
runtime = [r for r in rows if r.get("event") == "runtime_metrics"]
progress = [r for r in rows if r.get("event") == "websocket_receive_progress"]
decisions = [
    r for r in rows if r.get("event") == "strategy_decision_created" and r.get("active_strategy")
]
latest = runtime[-1] if runtime else {}
stopped = [r for r in rows if r.get("event") == "executed_evidence_stopped"]
output = {
    "latest_at": rows[-1].get("timestamp") if rows else None,
    "events": dict(Counter(r.get("event") for r in rows)),
    "active_decisions": len(decisions),
    "decision_actions": dict(Counter(r["action"] for r in decisions)),
    "decision_reasons": dict(Counter(reason for r in decisions for reason in r.get("reasons", []))),
    "executed_evidence": latest.get("executed_evidence"),
    "executed_final": stopped[-1] if stopped else None,
    "native_instructions": latest.get("native_instructions"),
    "queue_lag_max_ms": max((r.get("queue_lag_ms", 0) for r in progress), default=0),
    "loop_lag_max_ms": max((r.get("event_loop_lag_ms_peak", 0) for r in progress), default=0),
    "queue_peak": max((r.get("queue_peak", 0) for r in progress), default=0),
    "last_progress": progress[-1] if progress else None,
    "failures": [
        r
        for r in rows
        if r.get("event")
        in {
            "executed_processor_failed",
            "deferred_native_failed",
            "websocket_disconnect",
            "executed_evidence_unavailable",
            "executed_evidence_budget_exhausted",
        }
    ],
}
path.with_suffix(".metrics.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
print(json.dumps(output, indent=2))
