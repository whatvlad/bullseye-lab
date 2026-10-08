"""Retained-state classification plus <=20 selected native transaction reads."""
import asyncio
import gzip
import json
import random
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from memebot.core.config import Settings
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PumpTrade
from memebot.research.market_calibration import RequestBudget
from memebot.research.reserve_sync import ForensicRpc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"
CACHE = ROOT / "research_sessions/state-trust-20261001"
CACHE.mkdir(parents=True, exist_ok=True)


async def main():
    original = json.loads((OUT / "production_state_passive.json").read_text())
    mismatches, controls, previous = [], [], {}
    for row in original["observations"]:
        old = previous.get(row["market"])
        if row["continuity_status"] == "DIVERGED":
            delta = row["delta"]
            classification = "VIRTUAL_RESERVE_CHANGE" if set(delta) == {"virtual_quote"} else "UNKNOWN"
            mismatches.append({"row": row, "previous": old, "classification": classification,
                "physical_and_virtual_token_continuity_exact": set(delta) == {"virtual_quote"},
                "mayhem_state": "UNKNOWN", "mechanism": "UNKNOWN",
                "token_age": None, "collector_queue_pressure": "NOT_RETAINED",
                "log_truncation": "NOT_RETAINED", "instruction": "NOT_RETAINED"})
        elif row["venue"] == "pump_fun" and row["continuity_status"] == "EXACT":
            controls.append(row)
        previous[row["market"]] = row
    assert len(mismatches) == 117
    selected = sorted(mismatches, key=lambda c: abs(c["row"]["delta"].get("virtual_quote", 0)), reverse=True)[:4]
    for market in sorted({c["row"]["market"] for c in mismatches}):
        candidate = next(c for c in mismatches if c["row"]["market"] == market)
        if candidate not in selected and len(selected) < 16:
            selected.append(candidate)
    generator = random.Random(117)
    for candidate in generator.sample(mismatches, 2):
        if candidate not in selected and len(selected) < 18:
            selected.append(candidate)
    selected_rows = [c["row"] for c in selected] + generator.sample(controls, min(2, len(controls)))
    budget = RequestBudget(20)
    rpc = ForensicRpc(str(Settings().solana_rpc_http_url), budget)
    native = {}
    try:
        for row in selected_rows:
            signature = row["last_signature"]
            path = CACHE / f"transaction-{signature}.json.gz"
            if path.exists():
                tx = json.loads(gzip.decompress(path.read_bytes()))
            else:
                tx = await rpc._call("getTransaction", [signature, {"encoding": "json", "commitment": "finalized", "maxSupportedTransactionVersion": 127}])
                if tx is not None:
                    path.write_bytes(gzip.compress(json.dumps(tx).encode()))
            if tx is None:
                native[signature] = {"status": "UNAVAILABLE"}
                continue
            logs = tx["meta"].get("logMessages") or []
            events = extract_anchor_events(logs)
            ordinal = row["last_event_ordinal"]
            event = events[ordinal][1] if ordinal < len(events) else None
            native[signature] = {"status": "MATCHED" if isinstance(event, PumpTrade) else "DECODE_UNMATCHED",
                "is_mayhem_mode": event.is_mayhem_mode if isinstance(event, PumpTrade) else None,
                "instruction_name": event.instruction_name if isinstance(event, PumpTrade) else None,
                "event": asdict(event) if isinstance(event, PumpTrade) else None,
                "trade_event_count": sum(isinstance(e, PumpTrade) for _,e in events),
                "instruction_logs": [l for l in logs if l.startswith("Program log: Instruction:")],
                "truncated": any("Log truncated" in l for l in logs), "slot": tx["slot"]}
    finally:
        await rpc.close()
    for case in mismatches:
        evidence = native.get(case["row"]["last_signature"])
        if evidence:
            case["native_evidence"] = evidence
            case["mayhem_state"] = evidence.get("is_mayhem_mode")
            case["instruction"] = evidence.get("instruction_name")
            case["log_truncation"] = evidence.get("truncated")
    report = {"total_mismatches": len(mismatches),
        "classification_counts": dict(Counter(c["classification"] for c in mismatches)),
        "causal_mechanism_unknown_count": sum(c["mechanism"] == "UNKNOWN" for c in mismatches),
        "clusters": {"markets": len({c["row"]["market"] for c in mismatches}),
            "signatures": len({c["row"]["last_signature"] for c in mismatches}),
            "slots": dict(Counter(c["row"]["state_slot"] for c in mismatches)),
            "delta_fields": dict(Counter(','.join(c["row"]["delta"]) for c in mismatches)),
            "positive_delta": sum(c["row"]["delta"]["virtual_quote"] > 0 for c in mismatches)},
        "cases": mismatches, "native_sample": native, "selected_signatures": list(native),
        "provider_requests": rpc.calls, "max_new_rpc_requests": 20,
        "independent_failure_mechanisms_not_established": True}
    (OUT / "pumpfun_mismatch_classification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"total":117,"classifications":report["classification_counts"],"sampled_native":len(native),
        "sample_mode_flags":dict(Counter(str(e.get('is_mayhem_mode')) for e in native.values())),"rpc_reads":len(rpc.calls)}))


asyncio.run(main())
