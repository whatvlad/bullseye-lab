"""Executed Pump invocation/event coordinates. Presence is not proof of safety."""

from __future__ import annotations

from typing import Any

from memebot.providers.solana.encoding import decode_base58
from memebot.providers.solana.idl_schema import schema
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, PumpTrade, decode_anchor_event

EVENT_CPI_TAG = bytes.fromhex("e445a52e51cb9a1d")
TRADE_NAMES = frozenset(
    {"buy", "sell", "buy_exact_sol_in", "buy_v2", "sell_v2", "buy_exact_quote_in_v2"}
)


def account_keys(tx: dict[str, Any]) -> list[str]:
    loaded = tx["meta"].get("loadedAddresses", {})
    keys = (
        tx["transaction"]["message"]["accountKeys"]
        + loaded.get("writable", [])
        + loaded.get("readonly", [])
    )
    return [k["pubkey"] if isinstance(k, dict) else k for k in keys]


def trade_invocations(tx: dict[str, Any], mint: str) -> list[dict[str, Any]]:
    """Require exact emit-CPI payload inside the invocation's stack-height subtree."""
    keys = account_keys(tx)
    definitions = {bytes(i["discriminator"]): i for i in schema(PUMP_PROGRAM_ID)["instructions"]}
    groups = {g["index"]: g["instructions"] for g in tx["meta"].get("innerInstructions", [])}
    results = []
    for top_index, outer in enumerate(tx["transaction"]["message"]["instructions"]):
        inner = groups.get(top_index, [])
        items = [(None, outer), *enumerate(inner)]
        for inner_index, ix in items:
            if keys[ix["programIdIndex"]] != PUMP_PROGRAM_ID:
                continue
            raw = decode_base58(ix["data"])
            definition = definitions.get(raw[:8])
            if definition is None or definition["name"] not in TRADE_NAMES:
                continue
            accounts = [keys[i] for i in ix["accounts"]]
            mapping = dict(zip((a["name"] for a in definition["accounts"]), accounts, strict=False))
            if mapping.get("mint", mapping.get("base_mint")) != mint:
                continue
            height = 1 if inner_index is None else ix.get("stackHeight")
            if not isinstance(height, int):
                raise ValueError("ACCOUNT_ORDERING_AMBIGUITY: invocation stack height absent")
            descendants = []
            for pos in range(0 if inner_index is None else inner_index + 1, len(inner)):
                child = inner[pos]
                child_height = child.get("stackHeight")
                # RPC fixtures predating stack heights remain supported for a
                # direct top-level Pump call; nested calls require actual heights.
                if child_height is None and inner_index is None:
                    child_height = 2
                if not isinstance(child_height, int):
                    raise ValueError("ACCOUNT_ORDERING_AMBIGUITY: descendant stack height absent")
                if child_height <= height:
                    break
                descendants.append((pos, child))
            emitted = []
            for pos, child in descendants:
                if keys[child["programIdIndex"]] != PUMP_PROGRAM_ID:
                    continue
                data = decode_base58(child["data"])
                if data.startswith(EVENT_CPI_TAG):
                    event = decode_anchor_event(PUMP_PROGRAM_ID, data[8:])
                    if isinstance(event, PumpTrade) and event.mint == mint:
                        emitted.append((pos, event))
            if len(emitted) != 1:
                raise ValueError(
                    "EVENT_INSTRUCTION_ALIGNMENT: expected one matching TradeEvent CPI"
                )
            results.append(
                {
                    "top_index": top_index,
                    "inner_index": inner_index,
                    "stack_height": height,
                    "event_inner_index": emitted[0][0],
                    "event": emitted[0][1],
                    "instruction": ix,
                    "name": definition["name"],
                    "mapping": mapping,
                    "descendants": descendants,
                }
            )
    return results
