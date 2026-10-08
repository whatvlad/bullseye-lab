"""Three-valued offline policy experiments. These verdicts never authorize orders.

D deliberately removes historical/unknown-reach guards to measure their cost.
Its SHADOW_PASS can be unprovable; it is not a minimum safe paper gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from memebot.providers.solana.trade_alignment import account_keys

Truth = bool | None

CORE = (
    "standard_supported_route",
    "exact_anchor",
    "exact_reconstruction",
    "exact_parity",
    "exact_physical_accounting",
    "canonical_identity_config",
    "compatible_lifecycle_mode",
    "refresh_retained",
    "refresh_identity_config",
    "refresh_binding_compatible",
    "refresh_fresh",
    "current_state_consistent",
)


@dataclass(frozen=True)
class ShadowPolicy:
    name: str
    requirements: tuple[str, ...]
    authorization: Literal["NONE"] = "NONE"


POLICIES = {
    "STRICT": ShadowPolicy(
        "STRICT",
        (
            *CORE,
            "fence_1",
            "fence_2",
            "fence_3",
            "fence_4",
            "bounded_continuity",
            "terminal_bank_equal",
            "strict_invalidation_clear",
            "strict_refresh_approved",
        ),
    ),
    "STREAM_PLUS_TWO_FENCES": ShadowPolicy(
        "STREAM_PLUS_TWO_FENCES",
        (
            *CORE,
            "certified_stream_window",
            "relevant_mutation_window_closed",
            "fence_before_bank",
            "fence_after_bank",
            "bounded_continuity",
            "terminal_bank_equal",
            "strict_invalidation_clear",
            "no_unknown_protected_mutation",
        ),
    ),
    "STREAM_CURRENT_STATE": ShadowPolicy(
        "STREAM_CURRENT_STATE",
        (
            *CORE,
            "certified_stream_window",
            "relevant_mutation_window_closed",
            "bounded_continuity",
            "terminal_bank_equal",
            "strict_invalidation_clear",
            "no_unknown_protected_mutation",
        ),
    ),
    "CURRENT_STATE_ONLY_RESEARCH": ShadowPolicy("CURRENT_STATE_ONLY_RESEARCH", CORE),
}


def evaluate(facts: dict[str, Truth], policy: str) -> dict[str, Any]:
    definition = POLICIES[policy]
    missing = [key for key in definition.requirements if facts.get(key) is None]
    contradicted = [key for key in definition.requirements if facts.get(key) is False]
    accepted = not missing and not contradicted
    return {
        "policy": policy,
        "verdict": "SHADOW_PASS" if accepted else "SHADOW_REJECT",
        "shadow_pass": accepted,
        "missing_evidence": missing,
        "contradicted_requirements": contradicted,
        "requirements": definition.requirements,
        "authorizes_orders": False,
        "authorizes_live": False,
        "authorizes_experiment": False,
        "safety_proven": False,
    }


def transaction_write_scope(tx: dict[str, Any] | None, protected: set[str]) -> dict[str, Any]:
    """Conservative transaction envelope: no account outside it can be written.

    Intersection means MAY_WRITE, never proof of mutation. Missing envelope is
    UNKNOWN. No inference of account keys/write flags from a log instruction name.
    """
    if tx is None:
        return {"scope": "UNKNOWN", "fallback": "VENUE", "reason": "full packet absent"}
    try:
        message, meta = tx["transaction"]["message"], tx["meta"]
        header = message["header"]
        lookups = message.get("addressTableLookups", [])
        loaded = meta.get("loadedAddresses", {})
        if lookups:
            expected_writable = sum(len(row["writableIndexes"]) for row in lookups)
            expected_readonly = sum(len(row["readonlyIndexes"]) for row in lookups)
            if (
                len(loaded.get("writable", [])) != expected_writable
                or len(loaded.get("readonly", [])) != expected_readonly
            ):
                raise ValueError("unresolved lookup addresses")
        if meta.get("err") is not None or any("Log truncated" in s for s in meta["logMessages"]):
            raise ValueError("failed or incomplete packet")
        keys = account_keys(tx)
        count = len(message["accountKeys"])
        signed = header["numRequiredSignatures"]
        readonly_signed = header["numReadonlySignedAccounts"]
        readonly_unsigned = header["numReadonlyUnsignedAccounts"]
        if (
            not 0 <= readonly_signed <= signed <= count
            or not 0 <= readonly_unsigned <= count - signed
        ):
            raise ValueError("invalid header")
        writable = {
            key
            for i, key in enumerate(keys[:count])
            if i < signed - readonly_signed or signed <= i < count - readonly_unsigned
        }
        writable.update(meta.get("loadedAddresses", {}).get("writable", []))
        intersection = sorted(writable & protected)
        return {
            "scope": "MAY_WRITE_PROTECTED" if intersection else "PROVEN_NO_PROTECTED_WRITES",
            "protected_writable": intersection,
            "writable_accounts": sorted(writable),
            "account_envelope": keys,
            "fallback": "ACCOUNT_OR_MARKET" if intersection else "NO_COLLATERAL_INVALIDATION",
            "reason": "complete transaction account privilege envelope; all nested CPIs bounded",
        }
    except (KeyError, IndexError, TypeError, ValueError):
        return {"scope": "UNKNOWN", "fallback": "VENUE", "reason": "write envelope incomplete"}


def scoped_invalidation(
    scope: dict[str, Any], mode: str, *, target_market_bound: bool = False
) -> bool:
    """True means revoke. Unknown scope always revokes under every safe mode."""
    if mode == "GLOBAL_VENUE_INVALIDATION":
        return True
    if mode not in {"ACCOUNT_SCOPED_INVALIDATION", "MARKET_SCOPED_INVALIDATION"}:
        raise ValueError("unknown experimental scope mode")
    if scope["scope"] == "UNKNOWN":
        return True
    if scope["scope"] == "PROVEN_NO_PROTECTED_WRITES":
        return False
    # A market binding cannot override a writable Global/FeeConfig/creator account.
    # Broad account intersection remains conservative even for another market.
    return True
