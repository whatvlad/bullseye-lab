"""Summarize non-secret operational transport evidence without dumping log payloads."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
rows = []
raw = (root / "operational_stream_validation3.err.log").read_bytes()
log = raw.decode("utf-16" if raw.startswith(b"\xff\xfe") else "utf-8-sig")
for line in log.splitlines():
    try:
        rows.append(json.loads(line))
    except ValueError:
        pass
stopped = next((r for r in reversed(rows) if r.get("event") == "executed_evidence_stopped"), {})
progress = [r for r in rows if r.get("event") == "websocket_receive_progress"]
runtime = next((r for r in reversed(rows) if r.get("event") == "runtime_metrics"), {})
result = {
    "validation": json.loads((root / "operational_stream_validation.json").read_text()),
    "full_stream": {k: stopped.get(k) for k in ("metrics", "transport")},
    "native_progress": {
        "samples": len(progress),
        "max_sampled_queue_peak": max((r.get("queue_peak", 0) for r in progress), default=0),
        "max_sampled_queue_lag_ms": max((r.get("queue_lag_ms", 0) for r in progress), default=0),
        "last": progress[-1] if progress else None,
    },
    "native_instruction_counts": runtime.get("native_instructions"),
    "processor_errors": [r for r in rows if r.get("event") == "executed_processor_failed"],
}
(root / "operational_stream_validation3.summary.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
