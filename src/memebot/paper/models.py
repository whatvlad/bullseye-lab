from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from memebot.market_state import NormalizedMarketState
from memebot.models.market import LaunchVenue, MarketLifecycle


@dataclass(frozen=True, slots=True)
class ExecutionMarketSnapshot:
    mint: str
    market: str
    venue: LaunchVenue
    lifecycle: MarketLifecycle
    observed_at: datetime
    source_slot: int | None
    observed_price_raw: Decimal
    quote_asset: str
    real_token_reserves_raw: int | None
    real_quote_reserves_raw: int | None
    virtual_token_reserves_raw: int | None
    virtual_quote_reserves_raw: int | None
    curve_complete: bool = False
    price_source: str = "unknown"
    source_timestamp: datetime | None = None
    received_timestamp: datetime | None = None
    feed_timestamp: datetime | None = None
    feed_reference_price: Decimal | None = None
    price_source_disagreement_pct: Decimal | None = None
    data_quality: str = "unknown"
    rpc_state: str = "unknown"
    decision_price: Decimal | None = None
    feed_timestamp_estimated: bool = True
    normalized_state: NormalizedMarketState | None = None
    is_mayhem_mode: bool | None = None
    execution_state: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    portfolio_id: UUID
    currency: str
    initial_cash: Decimal
    cash_balance: Decimal
    realized_pnl: Decimal
    open_position_count: int


@dataclass(frozen=True, slots=True)
class PortfolioRiskSnapshot:
    portfolio_id: UUID
    initial_cash: Decimal
    open_cost_basis: Decimal
    unrealized_pnl: Decimal
    daily_realized_pnl: Decimal
    consecutive_losses: int
    last_closed_at: datetime | None
    mint_last_closed_at: datetime | None
    execution_marks_valid: bool = True


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    position_id: UUID
    portfolio_id: UUID
    mint: str
    strategy_key: str
    market: str
    venue: LaunchVenue
    lifecycle: MarketLifecycle
    token_quantity_raw: Decimal
    remaining_cost_basis: Decimal
    realized_pnl: Decimal
    entry_price_raw: Decimal
    peak_price_raw: Decimal
    opened_at: datetime
    partial_take_profit_taken: bool
    execution_mark: dict[str, Any] | None = None
