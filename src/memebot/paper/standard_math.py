"""Standard SOL Pump integer quotes, ported from official pump-sdk 2.0.0.

Rates come from candidate state; this module has no fixed 125 bps authorization.
"""

from __future__ import annotations

from typing import Any

from memebot.providers.solana.pump_idl import NATIVE_SOL_MINT, WRAPPED_SOL_MINT


def fee(amount: int, bps: int) -> int:
    if amount < 0 or not 0 <= bps <= 10000:
        raise ValueError("invalid integer fee input")
    return (amount * bps + 9999) // 10000


def select_fees(
    global_state: dict[str, Any], config: dict[str, Any], curve: dict[str, Any], supply: int
) -> dict[str, Any]:
    if curve["quote_mint"] not in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}:
        raise ValueError("unsupported quote")
    if supply <= 0 or curve["virtual_token_reserves"] <= 0:
        raise ValueError("invalid supply or reserves")
    tiers = config["fee_tiers"]
    thresholds = [tier["market_cap_lamports_threshold"] for tier in tiers]
    if not tiers or thresholds != sorted(set(thresholds)):
        raise ValueError("invalid fee schedule")
    market_cap = curve["virtual_quote_reserves"] * supply // curve["virtual_token_reserves"]
    tier = tiers[0]
    for row in tiers:
        if market_cap >= row["market_cap_lamports_threshold"]:
            tier = row
    protocol = int(tier["fees"]["protocol_fee_bps"])
    creator = int(tier["fees"]["creator_fee_bps"])
    override = int(curve["creator_fee_bps"])
    if global_state["creator_fee_configurable"] and override:
        if override > global_state["max_configurable_creator_fee_bps"]:
            raise ValueError("creator override exceeds config")
        creator = override
    if curve["creator"] == NATIVE_SOL_MINT:
        creator = 0
    if not 0 <= protocol + creator < 10000 or tier["fees"]["lp_fee_bps"] != 0:
        raise ValueError("unsupported curve fee")
    return {
        "protocol_bps": protocol,
        "creator_bps": creator,
        "market_cap_raw": market_cap,
        "tier_threshold": tier["market_cap_lamports_threshold"],
        "protocol_quality": "VERIFIED_AT_CANDIDATE_STATE",
        "creator_quality": "VERIFIED_AT_CANDIDATE_STATE",
    }


def buy_exact_tokens(curve: dict[str, Any], tokens: int, rates: dict[str, Any]) -> dict[str, int]:
    if not 0 < tokens <= curve["real_token_reserves"] or tokens >= curve["virtual_token_reserves"]:
        raise ValueError("buy reserve cap")
    net = tokens * curve["virtual_quote_reserves"] // (curve["virtual_token_reserves"] - tokens) + 1
    protocol, creator = fee(net, rates["protocol_bps"]), fee(net, rates["creator_bps"])
    return {
        "token_output": tokens,
        "net_curve_input": net,
        "protocol_fee": protocol,
        "creator_fee": creator,
        "gross_input": net + protocol + creator,
    }


def buy_quote(curve: dict[str, Any], gross: int, rates: dict[str, Any]) -> dict[str, int]:
    if gross <= 1:
        raise ValueError("buy budget too small")
    net = (gross - 1) * 10000 // (10000 + rates["protocol_bps"] + rates["creator_bps"])
    tokens = min(
        net * curve["virtual_token_reserves"] // (curve["virtual_quote_reserves"] + net),
        curve["real_token_reserves"],
    )
    quote = buy_exact_tokens(curve, tokens, rates)
    if quote["gross_input"] > gross:
        raise ValueError("integer quote exceeds budget")
    return {**quote, "budget": gross, "sdk_net_budget": net}


def buy_exact_input(curve: dict[str, Any], gross: int, rates: dict[str, Any]) -> dict[str, int]:
    """Native exact-input formula from the pinned buy_exact_sol_in IDL docs.

    This is not the SDK's exact-token quote used to construct a `buy` call.
    Reserve-cap completion is kept unsupported until its exact branch is proven.
    """
    if gross <= 1:
        raise ValueError("buy budget too small")
    net = gross * 10000 // (10000 + rates["protocol_bps"] + rates["creator_bps"])
    charges = fee(net, rates["protocol_bps"]) + fee(net, rates["creator_bps"])
    net -= max(0, net + charges - gross)
    if net <= 1:
        raise ValueError("exact-input net too small")
    tokens = (
        (net - 1) * curve["virtual_token_reserves"] // (curve["virtual_quote_reserves"] + net - 1)
    )
    if not 0 < tokens < curve["real_token_reserves"]:
        raise ValueError("unsupported exact-input reserve-cap branch")
    protocol, creator = fee(net, rates["protocol_bps"]), fee(net, rates["creator_bps"])
    return {
        "token_output": tokens,
        "net_curve_input": net,
        "protocol_fee": protocol,
        "creator_fee": creator,
        "gross_input": net + protocol + creator,
        "budget": gross,
    }


def sell_quote(curve: dict[str, Any], tokens: int, rates: dict[str, Any]) -> dict[str, int]:
    if tokens <= 0:
        raise ValueError("sell quantity invalid")
    gross = tokens * curve["virtual_quote_reserves"] // (curve["virtual_token_reserves"] + tokens)
    if gross <= 0 or gross > curve["real_quote_reserves"]:
        raise ValueError("sell reserve cap")
    protocol, creator = fee(gross, rates["protocol_bps"]), fee(gross, rates["creator_bps"])
    return {
        "token_input": tokens,
        "gross_output": gross,
        "protocol_fee": protocol,
        "creator_fee": creator,
        "net_output": gross - protocol - creator,
    }


def capped_sell_quote(curve: dict[str, Any], tokens: int, rates: dict[str, Any]) -> dict[str, int]:
    """Sell everything for the curve's remaining real SOL (dead-curve liquidation)."""
    gross = int(curve["real_quote_reserves"])
    if tokens <= 0 or gross <= 0:
        raise ValueError("sell reserve cap")
    protocol, creator = fee(gross, rates["protocol_bps"]), fee(gross, rates["creator_bps"])
    return {
        "token_input": tokens,
        "gross_output": gross,
        "protocol_fee": protocol,
        "creator_fee": creator,
        "net_output": gross - protocol - creator,
        "reserve_capped": 1,
    }
