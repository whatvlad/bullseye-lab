"""Scoped mutation evidence from native invocation frames, without transaction RPC."""

from __future__ import annotations

import base64
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

from memebot.market_state import InvalidationScope, MarketStateTracker

from .canonical import FEE_PROGRAM, config_addresses, curve_address, pda
from .encoding import BorshDecodeError, decode_base58
from .idl_schema import decode_record, instruction_schema
from .pump_idl import PUMP_AMM_PROGRAM_ID, PUMP_PROGRAM_ID, decode_anchor_event

PROGRAMS = {PUMP_PROGRAM_ID, PUMP_AMM_PROGRAM_ID, FEE_PROGRAM}
ORDINARY = {
    "Buy",
    "Sell",
    "BuyExactSolIn",
    "BuyExactQuoteIn",
    "BuyV2",
    "SellV2",
    "BuyExactQuoteInV2",
    # Not in the pinned IDL. Live V3 trades emit one standard TradeEvent plus the
    # emit-CPI, write no config account, and chain integer reserves exactly.
    "BuyV3",
    "SellV3",
    "BuyExactQuoteInV3",
}
_INVOKE = re.compile(r"^Program (\S+) invoke \[(\d+)]$")
_RETURN = re.compile(r"^Program (\S+) (?:success|failed:)")


def irrelevant_standard_fee_read(logs: list[str]) -> bool:
    """Discard fee-only reads for excluded venues, never an unknown fee write."""
    stack: list[str] = []
    fee_frames = 0
    fee_reads = 0
    for line in logs:
        if "Log truncated" in line:
            return False
        invoke = _INVOKE.match(line)
        returned = _RETURN.match(line)
        if invoke:
            program, depth = invoke.groups()
            if program == PUMP_PROGRAM_ID:
                return False
            del stack[int(depth) - 1 :]
            stack.append(program)
            fee_frames += program == FEE_PROGRAM
        elif returned:
            if stack and stack[-1] == returned.group(1):
                stack.pop()
            else:
                return False
        elif stack and stack[-1] == FEE_PROGRAM:
            if line.startswith("Program log: Instruction: "):
                name = line.removeprefix("Program log: Instruction: ")
                definition = instruction_schema(FEE_PROGRAM, name)
                if name not in {"GetFees", "GetFeesWithQuoteMint"} or definition is None:
                    return False
                if any(a.get("writable") for a in definition["accounts"]):
                    return False
                fee_reads += 1
            elif line.startswith("Program data: "):
                return False
    return not stack and fee_frames > 0 and fee_frames == fee_reads


@dataclass
class NativeFrame:
    program: str
    instruction: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    decoder_failure: bool = False
    parent: NativeFrame | None = None
    raw_events: list[bytes] = field(default_factory=list)
    children: int = 0


def native_frames(logs: list[str]) -> list[NativeFrame]:
    stack: list[NativeFrame] = []
    frames: list[NativeFrame] = []
    for line in logs:
        invoke, returned = _INVOKE.match(line), _RETURN.match(line)
        if invoke:
            program, depth = invoke.groups()
            del stack[int(depth) - 1 :]
            if stack:
                stack[-1].children += 1
            frame = NativeFrame(program, parent=stack[-1] if stack else None)
            stack.append(frame)
            if program in PROGRAMS:
                frames.append(frame)
        elif returned:
            indexes = [i for i, frame in enumerate(stack) if frame.program == returned.group(1)]
            if indexes:
                del stack[indexes[-1] :]
        elif stack and stack[-1].program in PROGRAMS:
            frame = stack[-1]
            if line.startswith("Program log: Instruction: "):
                frame.instruction = line.removeprefix("Program log: Instruction: ")
            elif line.startswith("Program data: "):
                try:
                    raw = base64.b64decode(line[14:], validate=True)
                    frame.raw_events.append(raw)
                    try:
                        name, values = decode_record(frame.program, raw, collection="events")
                        frame.events.append({"name": name, **values})
                    except BorshDecodeError:
                        event = decode_anchor_event(frame.program, raw)
                        if event is None:
                            frame.decoder_failure = True
                        else:
                            frame.events.append({"name": type(event).__name__, **asdict(event)})
                except (ValueError, BorshDecodeError, KeyError):
                    frame.decoder_failure = True
    return frames


def verified_event_cpi_frames(logs: list[str], transaction: dict[str, Any]) -> set[int]:
    """Identify emission calls by executed bytes, never by silent log shape alone."""
    try:
        meta = transaction["meta"]
        if meta["err"] is not None or meta["logMessages"] != logs:
            return set()
        message = transaction["transaction"]["message"]
        loaded = meta.get("loadedAddresses", {})
        keys = message["accountKeys"] + loaded.get("writable", []) + loaded.get("readonly", [])
        groups = {g["index"]: g["instructions"] for g in meta["innerInstructions"]}
        instructions = []
        for index, ix in enumerate(message["instructions"]):
            instructions.append((keys[ix["programIdIndex"]], 1, ix))
            for child in groups.get(index, []):
                instructions.append((keys[child["programIdIndex"]], child["stackHeight"], child))
        invocations = [m.groups() for line in logs if (m := _INVOKE.match(line))]
        if [(p, int(d)) for p, d in invocations] != [(p, d) for p, d, _ in instructions]:
            return set()
        native = [(p, ix) for p, _, ix in instructions if p in PROGRAMS]
        frames = native_frames(logs)
        if len(native) != len(frames):
            return set()
        verified = set()
        for index, (frame, (program, ix)) in enumerate(zip(frames, native, strict=True)):
            parent = frame.parent
            if (
                frame.instruction is not None
                or frame.decoder_failure
                or frame.events
                or parent is None
                or parent.program != program
                or parent.decoder_failure
                or parent.instruction not in ORDINARY
                or len(parent.raw_events) != 1
            ):
                continue
            accounts = [keys[i] for i in ix["accounts"]]
            if (
                accounts == [pda(program, [b"__event_authority"])]
                and decode_base58(ix["data"])
                == bytes.fromhex("e445a52e51cb9a1d") + parent.raw_events[0]
            ):
                verified.add(index)
        return verified
    except (KeyError, TypeError, ValueError, IndexError):
        return set()


def log_shape_event_cpi_frames(frames: list[NativeFrame]) -> set[int]:
    """Pump emit-CPI recognised by its strict log shape when no executed packet exists.

    Every retained full packet with this shape was byte-verified as the event CPI.
    A hidden reserve write would still break integer continuity on the next trade.
    """
    candidates = {
        index
        for index, frame in enumerate(frames)
        if frame.program == PUMP_PROGRAM_ID
        and frame.instruction is None
        and not frame.events
        and not frame.raw_events
        and not frame.decoder_failure
        and frame.children == 0
        and frame.parent is not None
        and frame.parent.program == frame.program
        and frame.parent.instruction in ORDINARY
        and not frame.parent.decoder_failure
        and len(frame.parent.raw_events) == 1
    }
    siblings = Counter(id(frames[index].parent) for index in candidates)
    return {index for index in candidates if siblings[id(frames[index].parent)] == 1}


def scope_native_mutations(
    logs: list[str],
    tracker: MarketStateTracker,
    *,
    signature: str | None,
    slot: int | None,
    transaction_index: int | None = None,
    transaction: dict[str, Any] | None = None,
    classification_counts: Counter[str] | None = None,
) -> None:
    frames = native_frames(logs)
    emissions = verified_event_cpi_frames(logs, transaction) if transaction is not None else set()
    truncated = any("Log truncated" in line for line in logs)
    shaped = log_shape_event_cpi_frames(frames) if transaction is None and not truncated else set()
    for index, frame in enumerate(frames):
        if index in emissions:
            if classification_counts is not None:
                classification_counts["VERIFIED_EVENT_CPI"] += 1
            continue
        if index in shaped:
            if classification_counts is not None:
                classification_counts["LOG_SHAPE_EVENT_CPI"] += 1
            continue
        if frame.instruction in ORDINARY and not frame.decoder_failure:
            continue
        if (
            frame.instruction == "SetMayhemVirtualParams"
            and not frame.decoder_failure
            and any(e["name"] == "UpdateMayhemVirtualParamsEvent" for e in frame.events)
        ):
            continue  # Applied in event order by the typed production mutation path.
        markets: set[str] = set()
        target_program = frame.program
        binding_events = list(frame.events)
        ancestor = frame.parent
        # A silent self-CPI is not assumed read-only. A proven native parent event
        # can still localize its uncertainty to the parent's market.
        if frame.instruction is None:
            while ancestor is not None:
                if ancestor.program == frame.program:
                    binding_events.extend(ancestor.events)
                    break
                ancestor = ancestor.parent
        for event in binding_events:
            if isinstance(event.get("pool"), str):
                markets.add(event["pool"])
            elif isinstance(event.get("bonding_curve"), str):
                markets.add(event["bonding_curve"])
            elif frame.program == PUMP_PROGRAM_ID and isinstance(event.get("mint"), str):
                markets.add(curve_address(event["mint"]))
            if frame.program == FEE_PROGRAM and event.get("fee_config"):
                for key, (address, _, _) in config_addresses().items():
                    if event["fee_config"] == address:
                        target_program = (
                            PUMP_PROGRAM_ID if key == "pump_fee" else PUMP_AMM_PROGRAM_ID
                        )
        definition = instruction_schema(frame.program, frame.instruction or "")
        writable = (
            {account["name"] for account in definition["accounts"] if account.get("writable")}
            if definition
            else set()
        )
        reserve_accounts = {
            "pool",
            "bonding_curve",
            "associated_bonding_curve",
            "pool_base_token_account",
            "pool_quote_token_account",
            "mint",
            "base_mint",
            "quote_mint",
        }
        config_accounts = {
            "global",
            "global_config",
            "fee_config",
            "quote_control",
            "sharing_config",
        }
        no_market_writes = (
            definition is not None
            and not writable.intersection(reserve_accounts | config_accounts)
            and not frame.decoder_failure
        )
        config_change = bool(writable.intersection(config_accounts)) or any(
            word in (frame.instruction or "")
            for word in ("Config", "Params", "Creator", "Admin", "Toggle")
        )
        reason = (
            "DECODER_FAILURE"
            if frame.decoder_failure
            else "KNOWN_NON_RESERVE_MUTATION"
            if no_market_writes
            else "MIGRATION"
            if "Migrat" in (frame.instruction or "")
            else "CONFIG_CHANGE"
            if config_change
            else "UNKNOWN_NATIVE_INSTRUCTION"
        )
        if classification_counts is not None:
            label = f"{reason}:{frame.program}:{(frame.instruction or 'SILENT')[:64]}"
            if label not in classification_counts and len(classification_counts) >= 128:
                label = "OTHER_CLASSIFICATION"
            classification_counts[label] += 1
        scope = (
            InvalidationScope.POOL
            if markets and frame.program == PUMP_AMM_PROGRAM_ID
            else InvalidationScope.MARKET
            if markets
            else InvalidationScope.VENUE
        )
        dimensions: tuple[str, ...] = (
            ()
            if no_market_writes
            else ("config",)
            if config_change and not writable.intersection(reserve_accounts)
            else ("reserves", "identity", "config")
        )
        if frame.program == FEE_PROGRAM and target_program == FEE_PROGRAM and not no_market_writes:
            scope = InvalidationScope.GLOBAL
            markets = set(tracker.states)
            dimensions = ("config",)
        tracker.invalidate(
            None,
            reason,
            scope=scope,
            program=target_program,
            signature=signature,
            slot=slot,
            transaction_index=transaction_index,
            affected_markets=markets if markets else set() if no_market_writes else None,
            dimensions=dimensions,
            scope_reason="native_event_market_binding"
            if markets
            else "IDL_no_relevant_writes"
            if no_market_writes
            else "native_program_known_market_unresolved",
        )
    if truncated:
        programs = {frame.program for frame in frames}
        if programs:
            for program in programs:
                tracker.invalidate(
                    None,
                    "TRUNCATED_LOG",
                    program=program,
                    signature=signature,
                    slot=slot,
                    transaction_index=transaction_index,
                    dimensions=("reserves",),
                    scope_reason="truncated_native_program_stream",
                )
        else:
            tracker.invalidate(
                None,
                "TRUNCATED_LOG",
                signature=signature,
                slot=slot,
                scope_reason="no_native_program_or_market_evidence",
            )
