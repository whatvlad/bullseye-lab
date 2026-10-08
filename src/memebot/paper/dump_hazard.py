from __future__ import annotations

from decimal import Decimal

from memebot.events.models import MarketFeatureSnapshotCreated, TokenTrade, TradeSide


def has_dump_hazard(
    trade: TokenTrade,
    feature: MarketFeatureSnapshotCreated | None,
    *,
    window_seconds: int = 30,
) -> bool:
    """Conservative, point-in-time dump overlay for already-open paper positions."""
    if (
        trade.side != TradeSide.SELL
        or feature is None
        or feature.mint != trade.mint
        or feature.source_event_at != trade.source_event_at
    ):
        return False
    metric = next(
        (item for item in feature.windows if item.window_seconds == window_seconds),
        None,
    )
    if metric is None or metric.trade_count < 6:
        return False
    sharp_price_drop = (
        metric.latest_price_return_percent is not None
        and metric.latest_price_return_percent <= Decimal("-8")
    )
    outlier_sell = (
        metric.latest_sell_size_mad_score is not None
        and metric.latest_sell_size_mad_score >= Decimal("6")
    )
    sustained_sell_pressure = (
        metric.flow_imbalance is not None and metric.flow_imbalance <= Decimal("-0.35")
    )
    window_drawdown = (
        metric.price_change_percent is not None and metric.price_change_percent <= Decimal("-12")
    )
    material_sell = (
        metric.latest_sell_quote_raw is not None
        and metric.latest_sell_quote_raw >= Decimal(100_000_000)
        and metric.latest_sell_liquidity_fraction is not None
        and metric.latest_sell_liquidity_fraction >= Decimal("0.02")
    )
    reserve_outflow = (
        metric.quote_reserve_change_raw is not None
        and metric.total_volume_quote_raw > 0
        and metric.quote_reserve_change_raw / metric.total_volume_quote_raw <= Decimal("-0.25")
    )
    return (sharp_price_drop or (outlier_sell and material_sell)) and (
        sustained_sell_pressure or window_drawdown or reserve_outflow
    )
