from __future__ import annotations

from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from memebot.models.common import DataAvailability, ProviderProvenance


class RiskEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=512)
    availability: DataAvailability = DataAvailability.AVAILABLE
    value: bool | int | Decimal | str | None = None
    severity: Literal["info", "warning", "hard_reject", "unknown"] = "info"
    threshold: Decimal | None = None
    provenance: ProviderProvenance | None = None

    @model_validator(mode="after")
    def validate_availability(self) -> Self:
        if self.availability == DataAvailability.AVAILABLE and self.value is None:
            raise ValueError("available risk evidence requires a value")
        if self.availability in {DataAvailability.UNKNOWN, DataAvailability.UNAVAILABLE}:
            if self.value is not None:
                raise ValueError("unknown risk evidence cannot carry a value")
            if self.severity != "unknown":
                raise ValueError("unknown risk evidence requires severity=unknown")
        return self


class RiskResult(BaseModel):
    """Risk is intentionally separate from opportunity scoring."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool | None
    risk_score: Decimal | None = Field(default=None, ge=0, le=100)
    data_completeness_percent: Decimal = Field(default=Decimal(0), ge=0, le=100)
    critical_unknowns: tuple[str, ...] = ()
    hard_reject_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: tuple[RiskEvidence, ...] = ()

    @model_validator(mode="after")
    def validate_hard_reject(self) -> RiskResult:
        if self.hard_reject_reasons and self.allowed is not False:
            raise ValueError("hard reject reasons require allowed=False")
        return self
