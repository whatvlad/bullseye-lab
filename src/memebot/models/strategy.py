from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from memebot.models.common import DataAvailability


class StrategyRegime(StrEnum):
    NEW_LAUNCH = "new_launch"
    EARLY_MOMENTUM = "early_momentum"
    BONDING_CURVE = "bonding_curve"
    FINAL_STRETCH = "final_stretch"
    GRADUATION = "graduation"
    POST_GRADUATION = "post_graduation"
    MATURE_MOMENTUM = "mature_momentum"
    DEAD_OR_ILLIQUID = "dead_or_illiquid"
    UNKNOWN = "unknown"


class StrategyDecisionAction(StrEnum):
    ENTER_CANDIDATE = "enter_candidate"
    WATCH = "watch"
    SKIP = "skip"


class ScoreEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=64)
    value: Decimal | int | str | bool | None = None
    message: str = Field(min_length=1, max_length=512)


class ScoreComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=32)
    availability: DataAvailability
    score: Decimal | None = Field(default=None, ge=0, le=100)
    configured_weight: Decimal = Field(ge=0, le=100)
    normalized_weight: Decimal | None = Field(default=None, ge=0, le=100)
    contribution: Decimal | None = Field(default=None, ge=0, le=100)
    reason: str | None = Field(default=None, max_length=512)
    evidence: tuple[ScoreEvidence, ...] = ()
    component_status: str = "LEGACY_UNKNOWN"
    missing_required_inputs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_availability(self) -> Self:
        if self.availability == DataAvailability.AVAILABLE and self.score is None:
            raise ValueError("available score component requires score")
        if self.availability != DataAvailability.AVAILABLE and self.score is not None:
            raise ValueError("unavailable score component cannot carry score")
        return self


class ScoreResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    final_score: Decimal | None = Field(default=None, ge=0, le=100)
    component_completeness_percent: Decimal = Field(ge=0, le=100)
    components: tuple[ScoreComponent, ...]
    overall_signal_completeness: Decimal = Field(default=Decimal(0), ge=0, le=100)
    missing_required_inputs: tuple[str, ...] = ()


class StrategyConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version_id: UUID
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")
    display_name: str = Field(min_length=1, max_length=64)
    version: int = Field(ge=1)
    enabled: bool = True
    active_for_execution: bool = False
    score_threshold: Decimal = Field(ge=0, le=100)
    watch_threshold: Decimal = Field(ge=0, le=100)
    maximum_risk_score: Decimal = Field(ge=0, le=100)
    minimum_component_completeness_percent: Decimal = Field(ge=0, le=100)
    minimum_token_age_seconds: int = Field(ge=0)
    minimum_trades_in_window: int = Field(ge=0)
    minimum_unique_buyers_in_window: int = Field(default=0, ge=0)
    minimum_observation_seconds: int = Field(default=0, ge=0)
    minimum_flow_imbalance: Decimal = Field(default=Decimal("0.20"), ge=-1, le=1)
    minimum_buyer_attribution_percent: Decimal = Field(default=Decimal(80), ge=0, le=100)
    maximum_largest_buyer_share: Decimal = Field(default=Decimal("0.50"), ge=0, le=1)
    require_sell_absorption: bool = False
    maximum_price_change_percent: Decimal | None = Field(default=None, gt=0)
    scoring_window_seconds: int = Field(gt=0)
    allowed_regimes: frozenset[StrategyRegime]
    component_weights: dict[str, Decimal]
    social_weight_enabled: bool = False

    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        if self.watch_threshold > self.score_threshold:
            raise ValueError("watch threshold cannot exceed entry threshold")
        base = {"momentum", "wallet", "risk", "social", "lifecycle", "market"}
        allowed = base | {"graduation_velocity"}
        if not base.issubset(self.component_weights) or not set(self.component_weights).issubset(
            allowed
        ):
            raise ValueError("strategy component weights define unsupported score categories")
        if any(weight < 0 for weight in self.component_weights.values()):
            raise ValueError("strategy component weights cannot be negative")
        if sum(self.component_weights.values(), start=Decimal(0)) != Decimal(100):
            raise ValueError("strategy component weights must sum to 100")
        return self
