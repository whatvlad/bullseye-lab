"""Deterministic classification of retained raw packets, never relaxed validity."""

from __future__ import annotations

from typing import Any

from memebot.providers.solana.alchemy_evidence import rpc_packet
from memebot.providers.solana.encoding import encode_base58
from memebot.providers.solana.evidence_stream import normalize_transaction
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, PumpTrade


def inspect_packet(update: Any, received_at: Any) -> dict[str, Any]:
    info = update.transaction.transaction
    accounts = [encode_base58(k) for k in info.transaction.message.account_keys]
    accounts += [encode_base58(k) for k in info.meta.loaded_writable_addresses]
    accounts += [encode_base58(k) for k in info.meta.loaded_readonly_addresses]
    result: dict[str, Any] = {"accounts": accounts, "category": "UNKNOWN", "usable": False}
    if not info.HasField("meta"):
        result["category"] = "MISSING_META"
        return result
    if not info.HasField("transaction"):
        result["category"] = "MALFORMED_PACKET"
        return result
    if PUMP_PROGRAM_ID not in accounts:
        result["category"] = "PROGRAM_FILTER_MISMATCH"
        return result
    if len(info.meta.pre_balances) != len(accounts) or len(info.meta.post_balances) != len(
        accounts
    ):
        result["category"] = (
            "ACCOUNT_KEY_RESOLUTION"
            if info.transaction.message.address_table_lookups
            else "BALANCE_SCHEMA"
        )
        return result
    if info.meta.inner_instructions_none or info.meta.log_messages_none:
        result["category"] = "MISSING_META"
        return result
    try:
        packet = rpc_packet(update)
        events = extract_anchor_events(packet["meta"]["logMessages"])
        trades = [e for _, e in events if isinstance(e, PumpTrade)]
        result["mints"] = [e.mint for e in trades]
        if len(trades) != 1:
            result["category"] = "NON_TRADE_EXECUTION" if not trades else "MULTI_EVENT_AMBIGUOUS"
            return result
        evidence = normalize_transaction(
            packet,
            slot=update.transaction.slot,
            signature=encode_base58(info.signature),
            index=info.index,
            source="raw_packet_forensics",
            commitment="confirmed",
            received_at=received_at,
        )
        result["category"] = "USABLE" if evidence is not None else "OUT_OF_SCOPE_EVENT"
        result["usable"] = evidence is not None
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        result["category"] = (
            "ADAPTER_BUG" if isinstance(error, (TypeError, AttributeError)) else "UNKNOWN"
        )
        if str(error).startswith(("malformed_v1", "invalid_v1")):
            result["category"] = "MALFORMED_PACKET"
        result["error_type"] = type(error).__name__
        result["error_detail"] = str(error)[:200]
    return result
