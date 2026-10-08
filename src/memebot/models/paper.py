from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from memebot.models.common import AwareUtcDatetime, ProviderProvenance


class PaperOrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class PaperOrderStatus(StrEnum):
    FILLED = "filled"
    REJECTED = "rejected"


class FillQuality(StrEnum):
    EXACT_ONCHAIN_MODEL = "exact_onchain_model"
    HIGH_CONFIDENCE = "high_confidence"
    ESTIMATED = "estimated"
    DEGRADED = "degraded"


class PositionEffect(StrEnum):
    OPEN = "open"
    PARTIAL_CLOSE = "partial_close"
    CLOSE = "close"
    NONE = "none"


class PaperExecutionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=64)
    value: Decimal | int | str | bool | None = None
    message: str = Field(min_length=1, max_length=512)
    provenance: ProviderProvenance | None = None


class PaperFill(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    signal_at: AwareUtcDatetime
    decision_at: AwareUtcDatetime
    submitted_at: AwareUtcDatetime
    filled_at: AwareUtcDatetime
    market_observed_at: AwareUtcDatetime
    quote_price_observed_at: AwareUtcDatetime
    quote_asset: str = Field(min_length=1, max_length=44)
    portfolio_currency: str = Field(min_length=3, max_length=8)
    quote_price_in_portfolio_currency: Decimal = Field(gt=0)
    observed_price_raw: Decimal = Field(gt=0)
    expected_fill_price_raw: Decimal = Field(gt=0)
    actual_fill_price_raw: Decimal = Field(gt=0)
    token_amount_raw: Decimal = Field(gt=0)
    gross_quote_amount_raw: Decimal = Field(gt=0)
    gross_portfolio_amount: Decimal = Field(gt=0)
    venue_fee_quote_raw: Decimal = Field(ge=0)
    execution_provider_fee_quote_raw: Decimal = Field(ge=0)
    network_fee_quote_raw: Decimal = Field(ge=0)
    total_fee_portfolio: Decimal = Field(ge=0)
    price_impact_bps: Decimal = Field(ge=0)
    total_price_deviation_bps: Decimal = Field(default=Decimal(0), ge=0)
    latency_slippage_bps: Decimal = Field(ge=0)
    simulated_latency_ms: int = Field(ge=0)
    fill_quality: FillQuality
    evidence: tuple[PaperExecutionEvidence, ...]
    price_source: str = "legacy_unknown"
    source_timestamp: AwareUtcDatetime | None = None
    received_timestamp: AwareUtcDatetime | None = None
    price_age_ms: int | None = None
    received_age_ms: int | None = None
    feed_age_ms: int | None = None
    price_source_disagreement_pct: Decimal | None = None
    data_quality: str = "legacy_unknown"
    state_source: str = "unknown"
    state_semantics: str = "UNKNOWN"
    state_quality: str = "UNKNOWN"
    state_slot: int | None = None
    reconciled_at: AwareUtcDatetime | None = None
    continuity_status: str = "UNKNOWN"
    state_reason: str | None = None
    identity_verified: bool = False
    observational_trust: str = "OBSERVATIONAL_INCOMPLETE"
    program: str | None = None
    is_mayhem_mode: bool | None = None
    multi_event_ambiguous: bool = False
    trading_universe: str = "STANDARD_PUMP_FUN_ONLY"
    entry_eligibility_status: str = "REJECTED"
    entry_rejection_reason: str | None = None
    execution_identity_verified: bool = False
    execution_config_verified: bool = False
    execution_assumptions_verified: bool = False
    invalidation_scope: str | None = None
    invalidation_reason: str | None = None
    feed_timestamp_estimated: bool | None = None
    price_model_version: int = 1
    decision_price: Decimal | None = None
    reference_price: Decimal | None = None
    executable_quote: Decimal | None = None
    simulated_fill: Decimal | None = None
    price_impact: Decimal | None = None
    slippage: Decimal | None = None
    fees: Decimal | None = None
    execution_state: dict[str, Any] | None = None
    exit_telemetry: dict[str, Any] = Field(default_factory=dict)
    execution_diagnostics: dict[str, Any] = Field(default_factory=dict)


class PaperOrderResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: PaperOrderStatus
    side: PaperOrderSide
    position_effect: PositionEffect
    requested_portfolio_amount: Decimal = Field(gt=0)
    rejection_reason: str | None = Field(default=None, max_length=512)
    exit_reason: str | None = Field(default=None, max_length=64)
    fill: PaperFill | None = None
    price_evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if self.status == PaperOrderStatus.FILLED:
            if self.fill is None or self.rejection_reason is not None:
                raise ValueError("filled paper order requires fill and no rejection")
            if self.position_effect == PositionEffect.NONE:
                raise ValueError("filled paper order requires a position effect")
            if self.side == PaperOrderSide.BUY and self.position_effect != PositionEffect.OPEN:
                raise ValueError("buy fill must open a position")
            if self.side == PaperOrderSide.SELL and self.position_effect not in {
                PositionEffect.CLOSE,
                PositionEffect.PARTIAL_CLOSE,
            }:
                raise ValueError("sell fill must close or partially close a position")
        else:
            if self.fill is not None or not self.rejection_reason:
                raise ValueError("rejected paper order requires reason and no fill")
            if self.position_effect != PositionEffect.NONE:
                raise ValueError("rejected paper order cannot affect a position")
        return self
