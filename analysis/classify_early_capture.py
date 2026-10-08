"""Replay every retained protobuf with hashes and representative rejection details."""
import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path

from memebot.providers.solana._yellowstone_generated import geyser_pb2 as proto
from memebot.research.packet_forensics import inspect_packet

parser = argparse.ArgumentParser()
parser.add_argument("capacity", choices=(8, 16, 32), type=int)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
counts = Counter()
examples = defaultdict(list)
inventory = []
with (ROOT / f"analysis/early_watch_{args.capacity}_packets.jsonl").open() as source:
    for line in source:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            break  # Live writer may not have completed its current line.
        if row.get("record_kind") != "provider_protobuf":
            continue
        raw = base64.b64decode(row["raw_protobuf_base64"], validate=True)
        update = proto.SubscribeUpdate.FromString(raw)
        result = inspect_packet(update, datetime.fromisoformat(row["received_timestamp"]))
        category = result["category"]
        counts[category] += 1
        entry = {"hash": hashlib.sha256(raw).hexdigest(), "signature": row["signature"],
                 "category": category, "details": {k: v for k, v in result.items() if k.startswith("error_")}}
        inventory.append(entry)
        if len(examples[category]) < 3:
            examples[category].append(entry)
output = {"capacity": args.capacity, "classifications": dict(counts),
          "representative_packets": dict(examples), "packet_inventory": inventory}
(ROOT / f"analysis/early_watch_{args.capacity}_decoder_forensics.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps({"classifications": dict(counts), "examples": dict(examples)}, indent=2))
