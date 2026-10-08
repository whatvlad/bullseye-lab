"""Generic transaction-scoped research proof. Never promotes production trades."""

from __future__ import annotations

from dataclasses import asdict
from itertools import pairwise
from typing import Any

from memebot.providers.solana.canonical import associated_address, curve_address
from memebot.providers.solana.encoding import decode_base58
from memebot.providers.solana.execution_accounting import execution_accounting
from memebot.providers.solana.idl_schema import schema
from memebot.providers.solana.pump import extract_anchor_events
from memebot.providers.solana.pump_idl import (
    PUMP_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    PumpTrade,
    decode_anchor_event,
)
from memebot.providers.solana.trade_alignment import trade_invocations

# Anchor's emit_cpi dispatch tag, distinct from native mutable instructions.
EVENT_CPI_TAG = bytes.fromhex("e445a52e51cb9a1d")


def reconstruct_transaction(transaction: dict[str, Any]) -> list[dict[str, Any]]:
    meta = transaction.get("meta") or {}
    logs = meta.get("logMessages") or []
    message = transaction.get("transaction", {}).get("message", {})
    loaded = meta.get("loadedAddresses", {})
    keys = message.get("accountKeys", []) + loaded.get("writable", []) + loaded.get("readonly", [])
    keys = [key.get("pubkey") if isinstance(key, dict) else key for key in keys]
    grouped: dict[str, list[PumpTrade]] = {}
    for _, event in extract_anchor_events(logs):
        if isinstance(event, PumpTrade):
            grouped.setdefault(event.mint, []).append(event)
    definitions = {
        bytes(row["discriminator"]): row for row in schema(PUMP_PROGRAM_ID)["instructions"]
    }
    reports = []
    for mint, events in grouped.items():
        curve = curve_address(mint)
        curve_vaults = {
            associated_address(curve, mint, program)
            for program in (TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID)
        }
        report: dict[str, Any] = {
            "mint": mint,
            "curve": curve,
            "status": "UNKNOWN",
            "event_count": len(events),
            "events": [asdict(e) for e in events],
            "reason": None,
            "production_promotion": False,
        }
        reports.append(report)
        if meta.get("err") is not None or any("Log truncated" in line for line in logs):
            report["reason"] = "FAILED_OR_TRUNCATED_TRANSACTION"
            continue
        if any(e.is_mayhem_mode is not False for e in events):
            report["reason"] = "MAYHEM_OR_MODE_UNKNOWN"
            continue
        native = []
        ambiguity = False
        if len(events) == 1:
            try:
                calls = trade_invocations(transaction, mint)
                if len(calls) != 1 or calls[0]["event"] != events[0]:
                    raise ValueError("EVENT_INSTRUCTION_ALIGNMENT: native and log event disagree")
                report["execution_alignment"] = [
                    {k: call[k] for k in ("top_index", "inner_index", "event_inner_index", "name")}
                    for call in calls
                ]
                report["transfer_accounting"] = execution_accounting(transaction, mint)
                native = [(calls[0]["top_index"], calls[0]["name"])]
            except (ValueError, KeyError, IndexError) as error:
                report["reason"] = str(error)
                continue
        for index, instruction in enumerate(message.get("instructions", [])):
            if len(events) == 1:
                break  # Single-event alignment and all movements checked above.
            accounts = [keys[item] for item in instruction.get("accounts", [])]
            if curve not in accounts and not curve_vaults.intersection(accounts):
                continue
            if keys[instruction["programIdIndex"]] != PUMP_PROGRAM_ID:
                ambiguity = True
                continue
            definition = definitions.get(decode_base58(instruction.get("data", ""))[:8])
            if definition is None or definition["name"] not in {
                "buy",
                "sell",
                "buy_exact_sol_in",
                "buy_v2",
                "sell_v2",
                "buy_exact_quote_in_v2",
            }:
                ambiguity = True
                continue
            if mint not in accounts:
                ambiguity = True
            native.append((index, definition["name"]))
        if ambiguity or len(native) != len(events):
            report["reason"] = "INSTRUCTION_EVENT_ORDER_OR_MUTATION_UNPROVEN"
            continue
        # Every self-CPI affecting this sequence must be the documented emit path
        # carrying the same typed event. Other native inner mutations stay UNKNOWN.
        emit_events = list(events) if len(events) == 1 else []
        for group in meta.get("innerInstructions", []):
            if len(events) == 1:
                break
            if group.get("index") not in {index for index, _ in native}:
                continue
            for instruction in group.get("instructions", []):
                if keys[instruction["programIdIndex"]] != PUMP_PROGRAM_ID:
                    continue
                raw = decode_base58(instruction.get("data", ""))
                if not raw.startswith(EVENT_CPI_TAG):
                    ambiguity = True
                    continue
                inner_event = decode_anchor_event(PUMP_PROGRAM_ID, raw[8:])
                if isinstance(inner_event, PumpTrade) and inner_event.mint == mint:
                    emit_events.append(inner_event)
        if (
            ambiguity
            or emit_events != events
            or any(
                (name.startswith("buy")) != event.is_buy
                for (_, name), event in zip(native, events, strict=True)
            )
        ):
            report["reason"] = "INNER_INSTRUCTION_OR_EMITTED_EVENT_AMBIGUITY"
            continue
        pre = [
            row
            for row in meta.get("preTokenBalances", [])
            if row.get("mint") == mint and row.get("owner") == curve
        ]
        post = [
            row
            for row in meta.get("postTokenBalances", [])
            if row.get("mint") == mint and row.get("owner") == curve
        ]
        if (
            len(pre) != 1
            or len(post) != 1
            or pre[0]["accountIndex"] != post[0]["accountIndex"]
            or curve not in keys
            or keys[pre[0]["accountIndex"]] not in curve_vaults
        ):
            report["reason"] = "CURVE_VAULT_METADATA_UNPROVEN"
            continue
        pre_token, post_token = (
            int(pre[0]["uiTokenAmount"]["amount"]),
            int(post[0]["uiTokenAmount"]["amount"]),
        )
        quote_delta = sum((1 if e.is_buy else -1) * e.quote_amount for e in events)
        token_delta = sum((-1 if e.is_buy else 1) * e.token_amount for e in events)
        curve_index = keys.index(curve)
        lamport_delta = meta["postBalances"][curve_index] - meta["preBalances"][curve_index]
        residuals = {
            "physical_token": post_token - pre_token - token_delta,
            "curve_lamports": lamport_delta - quote_delta,
        }
        for previous, current in pairwise(events):
            direction = 1 if current.is_buy else -1
            for name, amount, sign in (
                ("virtual_quote_reserves", current.quote_amount, direction),
                ("real_quote_reserves", current.quote_amount, direction),
                ("virtual_token_reserves", current.token_amount, -direction),
                ("real_token_reserves", current.token_amount, -direction),
            ):
                mismatch = getattr(current, name) - getattr(previous, name) - sign * amount
                if mismatch:
                    residuals[name] = mismatch
        reserved = post_token - events[-1].real_token_reserves
        quote_offset = meta["postBalances"][curve_index] - events[-1].real_quote_reserves
        report.update(
            residuals=residuals,
            reserved_inventory=reserved,
            nonreserve_lamport_offset=quote_offset,
            instruction_indices=[index for index, _ in native],
            vault=keys[pre[0]["accountIndex"]],
        )
        if any(residuals.values()) or reserved < 0 or quote_offset < 0:
            report["reason"] = "INTEGER_STATE_OR_PHYSICAL_BALANCE_MISMATCH"
            continue
        physical = pre_token
        sequence = []
        for event in events:
            physical += (-1 if event.is_buy else 1) * event.token_amount
            if physical - event.real_token_reserves != reserved:
                ambiguity = True
            sequence.append(
                {
                    "virtual_token": event.virtual_token_reserves,
                    "virtual_quote": event.virtual_quote_reserves,
                    "real_token": event.real_token_reserves,
                    "real_quote": event.real_quote_reserves,
                    "physical_vault": physical,
                }
            )
        if ambiguity:
            report["reason"] = "INTERMEDIATE_INVENTORY_INVARIANT_FAILED"
            continue
        report.update(
            status="TRANSACTION_SEQUENCE_VERIFIED",
            reason=None,
            intermediate_states=sequence,
            scope="THIS_TRANSACTION_ONLY",
            assumptions=(
                "Pinned native ordinary instruction semantics; "
                "no cross-transaction capture completeness claimed."
            ),
        )
    return reports
