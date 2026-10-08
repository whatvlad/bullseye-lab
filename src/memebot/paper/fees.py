from __future__ import annotations

from decimal import Decimal

from memebot.models.market import LaunchVenue

from .models import ExecutionMarketSnapshot

_LAMPORTS_PER_SOL = Decimal(1_000_000_000)
_PUMP_TOTAL_SUPPLY_RAW = Decimal(1_000_000_000_000_000)

# Official canonical PumpSwap SOL market-cap tiers, effective in 2026.
_PUMPSWAP_FEE_TIERS: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("420"), Decimal("125")),
    (Decimal("1470"), Decimal("120")),
    (Decimal("2460"), Decimal("115")),
    (Decimal("3440"), Decimal("110")),
    (Decimal("4420"), Decimal("105")),
    (Decimal("9820"), Decimal("100")),
    (Decimal("14740"), Decimal("95")),
    (Decimal("19650"), Decimal("90")),
    (Decimal("24560"), Decimal("85")),
    (Decimal("29470"), Decimal("80")),
    (Decimal("34380"), Decimal("75")),
    (Decimal("39300"), Decimal("70")),
    (Decimal("44210"), Decimal("65")),
    (Decimal("49120"), Decimal("60")),
    (Decimal("54030"), Decimal("55")),
    (Decimal("58940"), Decimal("52.5")),
    (Decimal("63860"), Decimal("50")),
    (Decimal("68770"), Decimal("47.5")),
    (Decimal("73681"), Decimal("45")),
    (Decimal("78590"), Decimal("42.5")),
    (Decimal("83500"), Decimal("40")),
    (Decimal("88400"), Decimal("37.5")),
    (Decimal("93330"), Decimal("35")),
    (Decimal("98240"), Decimal("32.5")),
    (Decimal("Infinity"), Decimal("30")),
)


def effective_venue_fee_bps(
    market: ExecutionMarketSnapshot,
    *,
    fallback_bps: Decimal,
) -> tuple[Decimal, str]:
    """Return the decision-time fee assumption and its provenance code."""
    if market.venue == LaunchVenue.PUMP_FUN:
        return Decimal("125"), "ESTIMATED_pump_fee_components_95_protocol_30_creator"
    if market.venue == LaunchVenue.PUMP_SWAP:
        market_cap_sol = pump_market_cap_sol(market.observed_price_raw)
        for upper_bound, fee_bps in _PUMPSWAP_FEE_TIERS:
            if market_cap_sol < upper_bound:
                return fee_bps, "official_canonical_pumpswap_market_cap_tier"
    return fallback_bps, "configured_fallback_venue_fee"


def pump_market_cap_sol(observed_price_raw: Decimal) -> Decimal:
    """Pump market cap: raw SOL price multiplied by the fixed 1B-token supply."""
    return observed_price_raw * _PUMP_TOTAL_SUPPLY_RAW / _LAMPORTS_PER_SOL
