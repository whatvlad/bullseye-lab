from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from memebot.core.clock import utc_now
from memebot.intelligence.features.models import RollingWindowMetrics
from memebot.market_state import NormalizedMarketState
from memebot.models.common import AwareUtcDatetime, SolanaAddress
from memebot.models.market import LaunchVenue, MarketLifecycle, MarketValidationState
from memebot.models.paper import PaperOrderResult
from memebot.models.risk import RiskResult
from memebot.models.strategy import (
    ScoreResult,
    StrategyDecisionAction,
    StrategyRegime,
)


class EventType(StrEnum):
    TOKEN_DISCOVERED = "token.discovered"
    TOKEN_TRADE = "token.trade"
    TOKEN_LIFECYCLE_CHANGED = "token.lifecycle_changed"
    PROVIDER_HEALTH_UPDATED = "provider.health_updated"
    MARKET_FEATURE_SNAPSHOT_CREATED = "market.feature_snapshot_created"
    TOKEN_RISK_ASSESSED = "token.risk_assessed"
    STRATEGY_DECISION_CREATED = "strategy.decision_created"
    PAPER_ACTION_PENDING = "paper.action_pending"
    PAPER_ACTION_EXPIRED = "paper.action_expired"
    PAPER_ORDER_COMPLETED = "paper.order_completed"


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class ProviderConnectionState(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class DomainEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    schema_version: int = Field(default=1, ge=1)
    provider: str = Field(min_length=1, max_length=64)
    source_event_at: AwareUtcDatetime
    source_timestamp_estimated: bool = False
    provider_received_at: AwareUtcDatetime | None = None
    ingested_at: AwareUtcDatetime = Field(default_factory=utc_now)
    correlation_id: UUID | None = None
    source_sequence: int | None = Field(default=None, ge=0)
    source_signature: str | None = Field(default=None, min_length=32, max_length=128)
    source_slot: int | None = Field(default=None, ge=0)


class TokenDiscovered(DomainEvent):
    event_type: Literal[EventType.TOKEN_DISCOVERED] = EventType.TOKEN_DISCOVERED
    mint: SolanaAddress
    name: str | None = Field(default=None, max_length=128)
    symbol: str | None = Field(default=None, max_length=32)
    creator: SolanaAddress | None = None
    launch_venue: LaunchVenue = LaunchVenue.UNKNOWN
    bonding_curve: SolanaAddress | None = None
    quote_mint: SolanaAddress | None = None
    metadata_uri: str | None = Field(default=None, max_length=1024)
    initial_real_token_reserves: int | None = Field(default=None, ge=0)
    token_total_supply: int | None = Field(default=None, ge=0)
    is_mayhem_mode: bool | None = None
    entry_rejection_reason: str | None = None


class TokenTrade(DomainEvent):
    entry_rejection_reason: str | None = None
    event_type: Literal[EventType.TOKEN_TRADE] = EventType.TOKEN_TRADE
    mint: SolanaAddress
    signature: str = Field(min_length=32, max_length=128)
    side: TradeSide
    token_amount: Decimal = Field(gt=0)
    quote_amount: Decimal = Field(gt=0)
    amounts_are_raw: Literal[True] = True
    quote_asset: str = Field(min_length=1, max_length=44)
    quote_mint: SolanaAddress | None = None
    wallet: SolanaAddress | None = None
    market: SolanaAddress | None = None
    real_token_reserves: int | None = Field(default=None, ge=0)
    real_quote_reserves: int | None = Field(default=None, ge=0)
    virtual_token_reserves: int | None = Field(default=None, ge=0)
    virtual_quote_reserves: int | None = None
    normalized_state: NormalizedMarketState = Field(default_factory=NormalizedMarketState)


class TokenLifecycleChanged(DomainEvent):
    event_type: Literal[EventType.TOKEN_LIFECYCLE_CHANGED] = EventType.TOKEN_LIFECYCLE_CHANGED
    mint: SolanaAddress
    lifecycle: MarketLifecycle
    validation_state: MarketValidationState
    bonding_progress_percent: Decimal | None = Field(default=None, ge=0, le=100)
    market: SolanaAddress | None = None
    quote_mint: SolanaAddress | None = None
    real_token_reserves: int | None = Field(default=None, ge=0)
    real_quote_reserves: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=512)
    is_mayhem_mode: bool | None = None
    entry_rejection_reason: str | None = None


class ProviderHealthUpdated(DomainEvent):
    http_status: int | None = Field(default=None, ge=100, le=599)
    event_type: Literal[EventType.PROVIDER_HEALTH_UPDATED] = EventType.PROVIDER_HEALTH_UPDATED
    state: ProviderConnectionState
    confirmed_capabilities: frozenset[str] = frozenset()
    unavailable_capabilities: frozenset[str] = frozenset()
    reconnect_count: int = Field(default=0, ge=0)
    average_message_latency_ms: Decimal | None = Field(default=None, ge=0)
    rate_limited: bool = False
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=512)


class MarketFeatureSnapshotCreated(DomainEvent):
    event_type: Literal[EventType.MARKET_FEATURE_SNAPSHOT_CREATED] = (
        EventType.MARKET_FEATURE_SNAPSHOT_CREATED
    )
    mint: SolanaAddress
    trigger_event_id: UUID
    lifecycle: MarketLifecycle = MarketLifecycle.UNKNOWN
    validation_state: MarketValidationState = MarketValidationState.DISCOVERED
    lifecycle_age_seconds: int | None = Field(default=None, ge=0)
    bonding_progress_percent: Decimal | None = Field(default=None, ge=0, le=100)
    market: SolanaAddress | None = None
    latest_price_raw: Decimal | None = Field(default=None, ge=0)
    windows: tuple[RollingWindowMetrics, ...]
    price_evidence: dict[str, Any] = Field(default_factory=dict)


class TokenRiskAssessed(DomainEvent):
    event_type: Literal[EventType.TOKEN_RISK_ASSESSED] = EventType.TOKEN_RISK_ASSESSED
    mint: SolanaAddress
    trigger_event_id: UUID
    market: SolanaAddress | None = None
    result: RiskResult
    current_execution_state: dict[str, Any] | None = None


class StrategyDecisionCreated(DomainEvent):
    event_type: Literal[EventType.STRATEGY_DECISION_CREATED] = EventType.STRATEGY_DECISION_CREATED
    mint: SolanaAddress
    strategy_key: str = Field(min_length=1, max_length=32)
    strategy_version_id: UUID
    active_strategy: bool
    action: StrategyDecisionAction
    regime: StrategyRegime
    risk_event_id: UUID
    feature_event_id: UUID | None = None
    score: ScoreResult
    reasons: tuple[str, ...]
    requested_position_percent: Decimal | None = Field(default=None, ge=0, le=100)
    decision_price: Decimal | None = None
    price_evidence: dict[str, Any] = Field(default_factory=dict)


class PaperOrderCompleted(DomainEvent):
    shadow_only: bool = False
    event_type: Literal[EventType.PAPER_ORDER_COMPLETED] = EventType.PAPER_ORDER_COMPLETED
    portfolio_id: UUID
    mint: SolanaAddress
    trigger_event_id: UUID
    decision_event_id: UUID | None = None
    strategy_key: str = Field(min_length=1, max_length=32)
    market: SolanaAddress | None = None
    venue: LaunchVenue
    lifecycle: MarketLifecycle
    result: PaperOrderResult


class PaperActionPending(DomainEvent):
    event_type: Literal[EventType.PAPER_ACTION_PENDING] = EventType.PAPER_ACTION_PENDING
    portfolio_id: UUID
    mint: SolanaAddress
    action: Literal["entry", "manual_close"]
    expires_at: AwareUtcDatetime
    reason: str = Field(min_length=1, max_length=128)
    decision_event_id: UUID | None = None


class PaperActionExpired(DomainEvent):
    event_type: Literal[EventType.PAPER_ACTION_EXPIRED] = EventType.PAPER_ACTION_EXPIRED
    portfolio_id: UUID
    mint: SolanaAddress
    action: Literal["entry", "manual_close"]
    reason: str = Field(min_length=1, max_length=128)
    decision_event_id: UUID | None = None
    requested_by_user_id: int | None = None


CoreEvent = Annotated[
    TokenDiscovered
    | TokenTrade
    | TokenLifecycleChanged
    | ProviderHealthUpdated
    | MarketFeatureSnapshotCreated
    | TokenRiskAssessed
    | StrategyDecisionCreated
    | PaperActionPending
    | PaperActionExpired
    | PaperOrderCompleted,
    Field(discriminator="event_type"),
]
_CORE_EVENT_ADAPTER: TypeAdapter[CoreEvent] = TypeAdapter(CoreEvent)


def parse_core_event(payload: dict[str, object]) -> CoreEvent:
    return _CORE_EVENT_ADAPTER.validate_python(payload)
