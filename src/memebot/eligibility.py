"""Standard Pump.fun entry universe. Exit recovery is deliberately independent."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

UNIVERSE = "STANDARD_PUMP_FUN_ONLY"


def paper_candidate_rejection(evidence: Mapping[str, Any], **context: Any) -> str | None:
    """Cheap hard exclusions before current-state verification, never fill authorization."""
    from memebot.providers.solana.pump_idl import PUMP_AMM_PROGRAM_ID, PUMP_PROGRAM_ID

    if evidence.get("is_mayhem_mode") is True:
        return "OUT_OF_SCOPE_MAYHEM"
    if context.get("venue") == "pump_swap" or evidence.get("program") == PUMP_AMM_PROGRAM_ID:
        return "OUT_OF_SCOPE_PUMPSWAP"
    if evidence.get("program") != PUMP_PROGRAM_ID or evidence.get("is_mayhem_mode") is not False:
        return "STATE_UNKNOWN"
    if (
        context.get("complete")
        or context.get("lifecycle") in {"graduation", "post_graduation", "mature"}
        or evidence.get("migrated")
    ):
        return "MIGRATED_MARKET"
    if evidence.get("multi_event_ambiguous"):
        return "MULTI_EVENT_AMBIGUOUS"
    reason = str(evidence.get("invalidation_reason") or evidence.get("state_reason") or "").upper()
    if any(
        word in reason
        for word in (
            "IDENTITY_MISMATCH",
            "UNSUPPORTED_ROUTE",
            "ROUTER",
            "MULTI_EVENT",
            "MIGRATION",
            "COMPLETION",
            "MALFORMED",
        )
    ):
        return "KNOWN_INCOMPATIBLE_OR_AMBIGUOUS_STATE"
    return None


def research_rejection(
    evidence: Mapping[str, Any],
    *,
    venue: str | None = None,
    lifecycle: str | None = None,
    mayhem: bool | None = None,
    complete: bool = False,
) -> str | None:
    # Provider package exports import the pump adapter; resolve constants only
    # after modules have loaded so policy can also be used by that adapter.
    from memebot.providers.solana.pump_idl import PUMP_AMM_PROGRAM_ID, PUMP_PROGRAM_ID

    mode = evidence.get("is_mayhem_mode") if mayhem is None else mayhem
    if mode is True or evidence.get("is_mayhem_mode") is True:
        return "OUT_OF_SCOPE_MAYHEM"
    if venue == "pump_swap" or evidence.get("program") == PUMP_AMM_PROGRAM_ID:
        return "OUT_OF_SCOPE_PUMPSWAP"
    if (
        complete
        or lifecycle in {"graduation", "post_graduation", "mature"}
        or evidence.get("migrated") is True
    ):
        return "MIGRATED_MARKET"
    if venue not in {None, "pump_fun"} or evidence.get("program") != PUMP_PROGRAM_ID:
        return (
            "OUT_OF_SCOPE_VENUE" if venue not in {None, "unknown", "pump_fun"} else "STATE_UNKNOWN"
        )
    if mode is not False:
        return "TOKEN_MODE_UNKNOWN"
    if (
        evidence.get("multi_event_ambiguous")
        or evidence.get("invalidation_reason") == "MULTI_EVENT_AMBIGUITY"
    ):
        return "MULTI_EVENT_AMBIGUOUS"
    if evidence.get("state_semantics") != "POST_TRADE":
        return "STATE_UNKNOWN"
    if evidence.get("state_quality") == "DIVERGED":
        return "CONTINUITY_DIVERGED"
    if evidence.get("state_quality") == "UNKNOWN":
        return "STATE_UNKNOWN"
    if evidence.get("continuity_status") == "DIVERGED":
        return "CONTINUITY_DIVERGED"
    if evidence.get("continuity_status") not in {"FIRST_OBSERVATION", "EXACT", "RPC_VALIDATED"}:
        return "STATE_UNKNOWN"
    return None


def entry_rejection(evidence: Mapping[str, Any], **context: Any) -> str | None:
    reason = research_rejection(evidence, **context)
    if reason:
        return reason
    if evidence.get("execution_identity_verified") is not True:
        return "IDENTITY_INCOMPLETE"
    if (
        evidence.get("execution_config_verified") is not True
        or evidence.get("execution_assumptions_verified") is not True
        or evidence.get("state_quality") != "HEALTHY"
    ):
        return "EXECUTION_STATE_INCOMPLETE"
    return None
