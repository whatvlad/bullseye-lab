from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RollingWindowMetrics(BaseModel):
    """Point-in-time metrics computed only from events at or before the watermark."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    window_seconds: int = Field(gt=0)
    trade_count: int = Field(ge=0)
    buy_count: int = Field(ge=0)
    sell_count: int = Field(ge=0)
    unique_buyers: int = Field(ge=0)
    unique_sellers: int = Field(ge=0)
    buy_volume_quote_raw: Decimal = Field(ge=0)
    sell_volume_quote_raw: Decimal = Field(ge=0)
    total_volume_quote_raw: Decimal = Field(ge=0)
    average_trade_quote_raw: Decimal | None = Field(default=None, ge=0)
    median_trade_quote_raw: Decimal | None = Field(default=None, ge=0)
    largest_buy_quote_raw: Decimal | None = Field(default=None, ge=0)
    largest_sell_quote_raw: Decimal | None = Field(default=None, ge=0)
    buy_sell_count_ratio: Decimal | None = Field(default=None, ge=0)
    buy_sell_volume_ratio: Decimal | None = Field(default=None, ge=0)
    flow_imbalance: Decimal | None = Field(default=None, ge=-1, le=1)
    open_price_raw: Decimal | None = Field(default=None, ge=0)
    close_price_raw: Decimal | None = Field(default=None, ge=0)
    price_change_percent: Decimal | None = None
    price_sample_count: int = Field(default=0, ge=0)
    missing_price_sample_count: int = Field(default=0, ge=0)
    price_observation_span_seconds: Decimal = Field(default=Decimal(0), ge=0)
    price_velocity_percent_per_second: Decimal | None = None
    price_acceleration_percent_per_second2: Decimal | None = None
    volume_velocity_quote_raw_per_second: Decimal = Field(ge=0)
    volume_acceleration_quote_raw_per_second2: Decimal = Decimal(0)
    transaction_rate_per_second: Decimal = Field(ge=0)
    transaction_rate_acceleration_per_second2: Decimal = Decimal(0)
    unique_buyer_rate_acceleration_per_second2: Decimal = Decimal(0)
    buy_pressure_acceleration_per_second: Decimal = Decimal(0)
    quote_reserve_change_raw: Decimal | None = None
    quote_reserve_velocity_raw_per_second: Decimal | None = None
    largest_buyer_volume_share: Decimal | None = Field(default=None, ge=0, le=1)
    buyer_volume_hhi: Decimal | None = Field(default=None, ge=0, le=1)
    buyer_wallet_attribution_percent: Decimal = Field(default=Decimal(0), ge=0, le=100)
    latest_price_return_percent: Decimal | None = None
    latest_sell_size_mad_score: Decimal | None = Field(default=None, ge=0)
    observation_span_seconds: Decimal = Field(default=Decimal(0), ge=0)
    latest_sell_quote_raw: Decimal | None = Field(default=None, ge=0)
    latest_sell_liquidity_fraction: Decimal | None = Field(default=None, ge=0)
