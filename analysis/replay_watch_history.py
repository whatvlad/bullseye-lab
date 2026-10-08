"""Bounded offline retention replay; no RPC and no invented missing packets."""
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from memebot.providers.solana.evidence_stream import EvidenceBuffer, normalize_transaction

ROOT = Path(__file__).resolve().parents[1]
old = json.loads((ROOT / "analysis/filtered_stream_pilot.json").read_text())
rows = [json.loads(line) for line in (ROOT / "analysis/filtered_stream_packets.jsonl").read_text().splitlines()]
events = []
markets = defaultdict(list)
for row in rows:
    evidence = normalize_transaction(row["packet"], slot=row["slot"], signature=row["signature"],
        index=row["transaction_index"], source="retained_offline_not_live", commitment="confirmed",
        received_at=datetime.fromisoformat(row["received_timestamp"]))
    if evidence:
        events.append(evidence)
        markets[evidence.mint].append(evidence)
windows = []
for pair in old["pairs"]:
    candidate = pair["NEW"]["candidate"]
    end = datetime.fromisoformat(candidate["detected_at"])
    start = end - timedelta(seconds=float(candidate["quality_evidence"]["metric"]["window_seconds"]))
    windows.append((candidate["mint"], start, end))
results = []
for capacity in (64, 128, 256):
    buffer = EvidenceBuffer(per_market=capacity)
    for event in events:
        buffer.add(event)
    drops = [e for e in buffer.evictions if "OVERFLOW" in e["reason"]]
    intersect = [e for e in drops if any(m == e["mint"] and start <= datetime.fromisoformat(e["received_at"]) <= end
        for m, start, end in windows)]
    results.append({"per_market_count_limit": capacity, "overflow_events_discarded": len(drops),
        "discarded_in_candidate_feature_windows": len(intersect), "evictions": drops,
        "retained_bytes": buffer.total_bytes, "retained_events": len(buffer.items)})
output = {"historical_raw_rejects_unavailable": 98,
    "replay_source": "147 retained normalized packets only; historical 98 rejects cannot be reconstructed",
    "markets": {mint: {"events": len(items), "time_span_seconds": (items[-1].received_at - items[0].received_at).total_seconds(),
        "events_per_second": len(items) / max(1, (items[-1].received_at - items[0].received_at).total_seconds()),
        "mean_normalized_payload_bytes": sum(len(json.dumps(e.transaction).encode()) for e in items)/len(items)}
        for mint, items in markets.items()}, "retention_replay": results}
(ROOT / "analysis/early_watch_historical_retention.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps({"retention_replay": [{k: v for k, v in r.items() if k != "evictions"} for r in results],
                  "largest_market_event_count": max(len(e) for e in markets.values())}, indent=2))
