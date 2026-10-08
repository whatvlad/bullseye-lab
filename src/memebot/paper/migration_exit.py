"""Atomic, sell-only recovery for a standard Pump position after graduation.

Quote math follows @pump-fun/pump-swap-sdk 1.20.0 sellBaseInput.
This never authorizes discovery or new PumpSwap entries.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Any

from memebot.market_state import NormalizedMarketState, ReserveSemantics, StateStatus
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.providers.solana.bootstrap import decode_config
from memebot.providers.solana.canonical import (
    associated_address,
    config_addresses,
    curve_address,
    pool_address_and_bump,
    pool_authority,
)
from memebot.providers.solana.pump_idl import (
    NATIVE_SOL_MINT,
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
    decode_mint_account,
    decode_token_account,
)

from .candidate_proof import ReadRpc, validate_token_extensions
from .models import ExecutionMarketSnapshot
from .standard_math import fee


def migration_addresses(mint: str) -> tuple[str, int, list[str]]:
    pool, bump = pool_address_and_bump(0, pool_authority(mint), mint, WRAPPED_SOL_MINT)
    configs = config_addresses()
    return (
        pool,
        bump,
        [
            mint,
            curve_address(mint),
            pool,
            WRAPPED_SOL_MINT,
            associated_address(pool, mint, TOKEN_PROGRAM_ID),
            associated_address(pool, mint, TOKEN_2022_PROGRAM_ID),
            associated_address(pool, WRAPPED_SOL_MINT, TOKEN_PROGRAM_ID),
            configs["swap_global"][0],
            configs["swap_fee"][0],
        ],
    )


async def read_migration_exit(
    rpc: ReadRpc, market: ExecutionMarketSnapshot
) -> ExecutionMarketSnapshot:
    from memebot.core.clock import utc_now

    _, _, addresses = migration_addresses(market.mint)
    raw = await rpc._call(
        "getMultipleAccounts",
        [
            addresses,
            {
                "commitment": "confirmed",
                "encoding": "base64",
                "minContextSlot": market.source_slot or 0,
            },
        ],
    )
    return decode_migration_exit(market, raw, utc_now().isoformat())


def decode_migration_exit(
    market: ExecutionMarketSnapshot, raw: dict[str, Any], received_at: str
) -> ExecutionMarketSnapshot:
    pool_address, bump, addresses = migration_addresses(market.mint)
    slot = int(raw["context"]["slot"])
    if slot < (market.source_slot or 0) or len(raw["value"]) != len(addresses):
        raise ValueError("migration_atomic_slot_or_batch_invalid")
    accounts = dict(zip(addresses, raw["value"], strict=True))

    def data(address: str, owner: str) -> bytes:
        account = accounts.get(address)
        if not account or account["owner"] != owner or account["executable"]:
            raise ValueError("migration_account_owner_or_presence_invalid")
        return base64.b64decode(account["data"][0], validate=True)

    def record(address: str, owner: str, name: str) -> dict[str, Any]:
        fields, missing = decode_config(owner, data(address, owner), name)
        if missing:
            raise ValueError("migration_schema_incomplete")
        return fields

    mint_owner = (accounts.get(market.mint) or {}).get("owner")
    if mint_owner not in {TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID}:
        raise ValueError("migration_mint_owner_invalid")
    mint_bytes = data(market.mint, mint_owner)
    mint = decode_mint_account(mint_bytes)
    validate_token_extensions(mint_bytes, mint_owner, mint=True)
    quote_mint = decode_mint_account(data(WRAPPED_SOL_MINT, TOKEN_PROGRAM_ID))
    curve = record(curve_address(market.mint), PUMP_PROGRAM_ID, "BondingCurve")
    pool = record(pool_address, PUMP_AMM_PROGRAM_ID, "Pool")
    if (
        not mint.initialized
        # Holder burns are valid after graduation; fees use the actual current supply.
        or curve["token_total_supply"] != 1_000_000_000_000_000
        or not 0 < mint.supply <= curve["token_total_supply"]
        or mint.mint_authority is not None
        or mint.freeze_authority is not None
        or mint.decimals != 6
        or not quote_mint.initialized
        or quote_mint.decimals != 9
        or not curve["complete"]
        or curve["is_mayhem_mode"]
        or pool["is_mayhem_mode"]
        or curve["quote_mint"] not in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}
        or pool["index"] != 0
        or pool["creator"] != pool_authority(market.mint)
        or pool["pool_bump"] != bump
        or pool["base_mint"] != market.mint
        or pool["quote_mint"] != WRAPPED_SOL_MINT
        or pool["coin_creator"] != curve["creator"]
    ):
        raise ValueError("migration_canonical_identity_invalid")
    if any(curve.get(key) or pool.get(key) for key in ("is_cashback_coin", "is_holder_reward")):
        raise ValueError("migration_complex_fee_route_unsupported")
    base_vault = associated_address(pool_address, market.mint, mint_owner)
    quote_vault = associated_address(pool_address, WRAPPED_SOL_MINT, TOKEN_PROGRAM_ID)
    if (
        pool["pool_base_token_account"] != base_vault
        or pool["pool_quote_token_account"] != quote_vault
    ):
        raise ValueError("migration_vault_pda_mismatch")
    base_bytes, quote_bytes = data(base_vault, mint_owner), data(quote_vault, TOKEN_PROGRAM_ID)
    for value, owner in ((base_bytes, mint_owner), (quote_bytes, TOKEN_PROGRAM_ID)):
        validate_token_extensions(value, owner, mint=False)
        if len(value) < 165 or value[108] != 1:
            raise ValueError("migration_vault_frozen_or_uninitialized")
    base, quote = decode_token_account(base_bytes), decode_token_account(quote_bytes)
    if (
        base.owner != pool_address
        or quote.owner != pool_address
        or base.mint != market.mint
        or quote.mint != WRAPPED_SOL_MINT
    ):
        raise ValueError("migration_vault_binding_invalid")
    offset = int(pool["virtual_quote_reserves"])
    if base.amount <= 0 or quote.amount <= 0 or offset < 0:
        raise ValueError("migration_reserves_invalid")
    configs = config_addresses()
    global_state = record(configs["swap_global"][0], PUMP_AMM_PROGRAM_ID, "GlobalConfig")
    fee_config = record(configs["swap_fee"][0], configs["swap_fee"][1], "FeeConfig")
    # Conservative: no fill while the program reports any disabled instruction.
    if global_state["disable_flags"]:
        raise ValueError("migration_program_disabled")
    cap = (quote.amount + offset) * mint.supply // base.amount
    tiers = fee_config["fee_tiers"]
    thresholds = [row["market_cap_lamports_threshold"] for row in tiers]
    if not tiers or thresholds != sorted(set(thresholds)):
        raise ValueError("migration_fee_schedule_invalid")
    tier = tiers[0]
    for row in tiers:
        if cap >= row["market_cap_lamports_threshold"]:
            tier = row
    rates = {
        name: int(tier["fees"][field])
        for name, field in (
            ("lp_bps", "lp_fee_bps"),
            ("protocol_bps", "protocol_fee_bps"),
            ("creator_bps", "creator_fee_bps"),
        )
    }
    if global_state["creator_fee_configurable"] and pool["creator_fee_bps"]:
        if pool["creator_fee_bps"] > global_state["max_configurable_creator_fee_bps"]:
            raise ValueError("migration_creator_fee_invalid")
        rates["creator_bps"] = int(pool["creator_fee_bps"])
    if pool["coin_creator"] == NATIVE_SOL_MINT:
        rates["creator_bps"] = 0
    if any(rate < 0 for rate in rates.values()) or sum(rates.values()) >= 10000:
        raise ValueError("migration_fee_rates_invalid")
    version = ":".join(
        hashlib.sha256(data(configs[key][0], configs[key][1])).hexdigest()
        for key in ("swap_global", "swap_fee")
    )
    at = datetime.fromisoformat(received_at)
    state = NormalizedMarketState(
        market=pool_address,
        program=PUMP_AMM_PROGRAM_ID,
        base_mint=market.mint,
        state_source="atomic_migration_exit",
        reserve_semantics=ReserveSemantics.POST_TRADE,
        state_quality=StateStatus.HEALTHY,
        state_slot=slot,
        reconciled_at=at,
        quote_reserve=quote.amount,
        token_reserve=base.amount,
        virtual_offset=offset,
        continuity_status="RPC_VALIDATED",
        identity_verified=True,
        is_mayhem_mode=False,
        execution_identity_verified=True,
        execution_config_verified=True,
        execution_assumptions_verified=True,
    )
    execution = dict(
        model="canonical_pumpswap_exit",
        sell_only=True,
        slot=slot,
        pool=pool,
        curve=curve,
        rates=rates,
        reserves={"base": base.amount, "quote": quote.amount, "offset": offset},
        binding={
            "config_version": version,
            "mint": market.mint,
            "pool": pool_address,
            "base_vault": base_vault,
            "quote_vault": quote_vault,
        },
        account_batch={"addresses": addresses, "response": raw, "received_at": received_at},
    )
    return replace(
        market,
        market=pool_address,
        venue=LaunchVenue.PUMP_SWAP,
        lifecycle=MarketLifecycle.POST_GRADUATION,
        curve_complete=False,
        observed_at=at,
        source_slot=slot,
        received_timestamp=at,
        source_timestamp=None,
        observed_price_raw=Decimal(quote.amount + offset) / Decimal(base.amount),
        price_source="atomic_migration_exit",
        rpc_state="healthy",
        data_quality="canonical_atomic_migration_exit_verified",
        normalized_state=state,
        execution_state=execution,
        is_mayhem_mode=False,
        real_token_reserves_raw=base.amount,
        real_quote_reserves_raw=quote.amount,
        virtual_token_reserves_raw=None,
        virtual_quote_reserves_raw=offset,
        price_source_disagreement_pct=None,
    )


def migration_sell_quote(state: dict[str, Any], tokens: int) -> dict[str, int]:
    reserves, rates = state["reserves"], state["rates"]
    if tokens <= 0:
        raise ValueError("migration_sell_quantity_invalid")
    gross = tokens * (reserves["quote"] + reserves["offset"]) // (reserves["base"] + tokens)
    lp, protocol, creator = (
        fee(gross, rates[key]) for key in ("lp_bps", "protocol_bps", "creator_bps")
    )
    if gross <= lp + protocol + creator or gross - lp > reserves["quote"]:
        raise ValueError("migration_sell_liquidity_unavailable")
    return dict(
        token_input=tokens,
        gross_output=gross,
        lp_fee=lp,
        protocol_fee=protocol,
        creator_fee=creator,
        net_output=gross - lp - protocol - creator,
    )
