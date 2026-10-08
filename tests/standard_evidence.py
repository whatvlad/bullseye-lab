"""Explicit execution-approved standard fixtures; never used by production."""

from memebot.market_state import NormalizedMarketState, ReserveSemantics, StateStatus
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID


def approved_state():
    return NormalizedMarketState(
        program=PUMP_PROGRAM_ID,
        is_mayhem_mode=False,
        reserve_semantics=ReserveSemantics.POST_TRADE,
        continuity_status="EXACT",
        state_quality=StateStatus.HEALTHY,
        execution_identity_verified=True,
        execution_config_verified=True,
        execution_assumptions_verified=True,
        virtual_token=100_000_000_000,
        virtual_quote=10_000_000_000,
    )


def approved_evidence():
    return {**approved_state().evidence(), "data_quality": "source_time_reported"}


def atomic_market(market):
    """Synthetic verified bank for execution/risk unit tests; never live truth."""
    from dataclasses import replace

    curve = {
        "virtual_token_reserves": market.virtual_token_reserves_raw,
        "virtual_quote_reserves": market.virtual_quote_reserves_raw,
        "real_token_reserves": market.real_token_reserves_raw,
        "real_quote_reserves": market.real_quote_reserves_raw,
    }
    return replace(
        market,
        execution_state={
            "curve": curve,
            "rates": {"protocol_bps": 95, "creator_bps": 30},
            "slot": market.source_slot,
            "binding": {"config_version": "SYNTHETIC_UNIT_TEST"},
        },
        normalized_state=market.normalized_state or approved_state(),
        received_timestamp=market.received_timestamp or market.observed_at,
        rpc_state="healthy" if market.rpc_state == "unknown" else market.rpc_state,
        is_mayhem_mode=False,
    )
