"""At most five native block reads to fill a previously uncached six-slot gap."""
import asyncio
import json
from pathlib import Path

from memebot.core.config import Settings
from memebot.research.market_calibration import RequestBudget
from memebot.research.reserve_sync import ForensicRpc, block_read, transaction_events, verify_semantics

ROOT = Path(__file__).resolve().parents[1]


async def main():
    prior = json.loads((ROOT / "analysis/live_transition_forensics.json").read_text())["results"][0]
    rows = prior["all_market_native_events"]
    previous = next(r for r in rows if r["signature"] + ":" + str(r["event_ordinal"]) == prior["previous_event_id"])
    current = next(r for r in rows if r["signature"] + ":" + str(r["event_ordinal"]) == prior["current_event_id"])
    slots = list(range(previous["slot"] + 1, current["slot"]))
    assert len(slots) <= 5
    budget = RequestBudget(5)
    rpc = ForensicRpc(str(Settings().solana_rpc_http_url), budget)
    recovered = []
    unavailable = []
    try:
        for slot in slots:
            block = await block_read(rpc, slot, ROOT / "research_sessions/reserve-sync-20261001")
            if block is None:
                unavailable.append(slot)
                continue
            recovered.extend(r for r in transaction_events(block, slot) if r["event"].get("pool") == prior["market"])
    finally:
        await rpc.close()
    all_rows = [previous, *recovered, current]
    all_rows.sort(key=lambda r: (r["slot"], r["transaction_index"], r["event_ordinal"]))
    verify_semantics(all_rows, {})
    residual = []
    for left, right in zip(all_rows, all_rows[1:]):
        post = left.get("expected_post_from_event_fields")
        pre = right["reported_reserves"]
        if post is not None:
            delta = {k: pre[k] - v for k, v in post.items() if pre[k] != v}
            if delta:
                residual.append({"left": left["signature"], "right": right["signature"], "delta": delta})
    result = {"market": prior["market"], "previous_slot": previous["slot"], "current_slot": current["slot"],
        "previously_missing_block_slots": slots, "unavailable_slots": unavailable,
        "recovered_intervening_trade_count": len(recovered), "events": recovered,
        "remaining_integer_breaks": residual, "loss_layer": "UNKNOWN",
        "cause": "INTERVENING_NATIVE_TRADES_IN_UNCACHED_SLOTS" if recovered and not unavailable and not residual else "UNKNOWN",
        "provider_requests": rpc.calls, "max_new_rpc_reads": 5}
    (ROOT / "analysis/remaining_state_break.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k not in {"events", "provider_requests"}}))


asyncio.run(main())
