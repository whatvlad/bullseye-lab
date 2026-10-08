from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from memebot.models.market import MarketLifecycle, MarketValidationState
from memebot.providers.solana.pump_idl import MintAccountState


@dataclass(frozen=True, slots=True)
class LocalRiskContext:
    mint: str
    creator: str | None
    market: str | None
    quote_mint: str | None
    lifecycle: MarketLifecycle
    validation_state: MarketValidationState
    observed_at: datetime
    source_slot: int | None
    creator_launches: int
    creator_graduations: int
    creator_rejections: int
    early_unique_buyers: int
    largest_early_buyer_share_percent: Decimal | None
    largest_synchronized_buyer_group: int


@dataclass(frozen=True, slots=True)
class OnChainRiskFacts:
    observed_at: datetime
    source_slot: int | None
    mint_state: MintAccountState | None
    mint_error: str | None
    top1_holder_percent: Decimal | None
    top5_holder_percent: Decimal | None
    top10_holder_percent: Decimal | None
    holder_error: str | None
    circulating_supply_raw: int | None
    creator_holding_percent: Decimal | None
    creator_holding_error: str | None
    available_quote_reserves_raw: int | None
    liquidity_error: str | None
    excluded_market_token_accounts: int
