"""Offline replay and bounded primary-IDL mutation inventory; no database writes."""
import base64
import gzip
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import httpx

from memebot.market_state import MarketStateTracker, normalize_trade
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PumpSwapTrade, PumpTrade

ROOT = Path(__file__).resolve().parents[1]
cache = ROOT / "research_sessions/reserve-sync-20261001"
anomalies = json.loads((ROOT / "analysis/reserve_anomalies.json").read_text())
breaks = json.loads((ROOT / "analysis/live_transition_forensics.json").read_text())["results"]
blocks = {}


def block(slot):
    if slot not in blocks:
        blocks[slot] = json.loads(gzip.decompress((cache / f"block-{slot}.json.gz").read_bytes()))
    return blocks[slot]


def transaction(slot, signature):
    return next(tx for tx in block(slot)["transactions"] if signature in tx["transaction"]["signatures"])


def native(row):
    tx = transaction(row["slot"], row["signature"])
    events = extract_anchor_events(tx["meta"]["logMessages"])
    return events[row["event_ordinal"]][1], events


results = []
for case in anomalies["results"]:
    row = case.get("target_trade")
    if row is None:
        results.append({"selection": case["selection"], "status": "UNMATCHED"})
        continue
    event, events = native(row)
    market = event.pool if isinstance(event, PumpSwapTrade) else case["sample"]["market"]
    multi = isinstance(event, PumpTrade) and sum(isinstance(e, PumpTrade) and e.mint == event.mint for _, e in events) > 1
    state = normalize_trade(event, market=market, slot=row["slot"], signature=row["signature"], ordinal=row["event_ordinal"], multi_event_unknown=multi)
    raw = row["reported_reserves"]
    raw_price = (raw["real_quote"] + raw.get("virtual_offset", 0)) / raw["real_token"] if isinstance(event, PumpSwapTrade) else raw["virtual_quote"] / raw["virtual_token"]
    results.append({"selection": case["selection"], "signature": row["signature"], "slot": row["slot"],
        "original_semantic": row.get("semantic"), "multi_event": multi,
        "normalized": state.model_dump(mode="json"), "raw_event_price": raw_price,
        "production_post_price": str(state.observational_price) if state.observational_price else None,
        "original_cause": case["cause"], "percentage_threshold_eligible": False,
        "transaction_trade_count": len([e for _, e in events if isinstance(e, PumpTrade) and getattr(e, "mint", None) == getattr(event, "mint", None)]) if isinstance(event, PumpTrade) else None,
    })

continuity_cases = []
for case in breaks:
    tracker = MarketStateTracker()
    rows = case["all_market_native_events"]
    wanted = {case["previous_event_id"], case["current_event_id"]}
    states = []
    metadata = []
    for row in rows:
        if f'{row["signature"]}:{row["event_ordinal"]}' not in wanted:
            continue
        event, _ = native(row)
        normalized = tracker.observe(event, market=case["market"], slot=row["slot"], signature=row["signature"], ordinal=row["event_ordinal"])
        states.append(normalized.model_dump(mode="json"))
        tx = transaction(row["slot"], row["signature"])
        pre = {b["accountIndex"]: b for b in tx["meta"].get("preTokenBalances", []) if b.get("owner") == case["market"]}
        post = {b["accountIndex"]: b for b in tx["meta"].get("postTokenBalances", []) if b.get("owner") == case["market"]}
        metadata.append({"signature": row["signature"], "slot": row["slot"],
            "vault_balances": [{"mint": b["mint"], "pre": int(b["uiTokenAmount"]["amount"]), "post": int(post[index]["uiTokenAmount"]["amount"])} for index, b in pre.items() if index in post],
            "instruction_logs": [l for l in tx["meta"]["logMessages"] if l.startswith("Program log: Instruction:")],
        })
    continuity_cases.append({"market": case["market"], "previous": case["previous_event_id"],
        "current": case["current_event_id"], "prior_cause": case["cause"],
        "missing_native_events": case["absent_from_passive_capture"],
        "production_replay": states, "native_metadata": metadata,
        "loss_layer": "UNKNOWN", "nontrade_mutation_proven": False,
    })

# Two primary documentation requests, separate from paid/native RPC accounting.
inventories = []
for name in ("pump", "pump_amm"):
    url = f"https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/{name}.json"
    try:
        response = httpx.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        inventories.append({"url": url, "sha256": hashlib.sha256(response.content).hexdigest(),
            "instructions": [{"name": ix["name"], "discriminator": ix["discriminator"],
                "writable_accounts": [a["name"] for a in ix["accounts"] if a.get("writable")]} for ix in data["instructions"]],
            "events": [e["name"] for e in data["events"]],
        })
    except httpx.HTTPError as error:
        inventories.append({"url": url, "error": type(error).__name__})

report = {"mode": "OFFLINE_PRODUCTION_NORMALIZATION_REPLAY", "replayed_cases": len(results),
    "semantics": dict(Counter(r.get("normalized", {}).get("reserve_semantics", "UNMATCHED") for r in results)),
    "cases": results, "continuity_breaks": continuity_cases,
    "primary_idl_inventory": inventories, "documentation_requests": 2,
    "new_rpc_requests": 0, "original_threshold_pairs_still_ineligible": True}
(ROOT / "analysis/production_state_replay.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
print(json.dumps({k: report[k] for k in ("replayed_cases", "semantics", "new_rpc_requests")}))
