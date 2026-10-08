from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from memebot.models.common import AwareUtcDatetime, SolanaAddress


class LaunchVenue(StrEnum):
    PUMP_FUN = "pump_fun"
    PUMP_SWAP = "pump_swap"
    RAYDIUM = "raydium"
    ORCA = "orca"
    OTHER = "other"
    UNKNOWN = "unknown"


class MarketLifecycle(StrEnum):
    NEW_LAUNCH = "new_launch"
    BONDING_CURVE = "bonding_curve"
    FINAL_STRETCH = "final_stretch"
    GRADUATION = "graduation"
    POST_GRADUATION = "post_graduation"
    MATURE = "mature"
    DEAD_OR_ILLIQUID = "dead_or_illiquid"
    UNKNOWN = "unknown"


class MarketValidationState(StrEnum):
    DISCOVERED = "discovered"
    VALIDATING = "validating"
    VERIFIED_MARKET_DATA = "verified_market_data"
    INSUFFICIENT_DATA = "insufficient_data"
    REJECTED = "rejected"


class TokenIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mint: SolanaAddress
    name: str | None = Field(default=None, max_length=128)
    symbol: str | None = Field(default=None, max_length=32)
    creator: SolanaAddress | None = None
    created_at: AwareUtcDatetime | None = None
    launch_venue: LaunchVenue = LaunchVenue.UNKNOWN
    quote_mint: SolanaAddress | None = None


class MarketSnapshot(BaseModel):
    """Small cross-phase market state contract; full features arrive in Phase 2."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mint: SolanaAddress
    observed_at: AwareUtcDatetime
    lifecycle: MarketLifecycle = MarketLifecycle.UNKNOWN
    validation_state: MarketValidationState = MarketValidationState.DISCOVERED
    market_address: SolanaAddress | None = None
    venue: LaunchVenue = LaunchVenue.UNKNOWN
    token_age_seconds: int | None = Field(default=None, ge=0)
