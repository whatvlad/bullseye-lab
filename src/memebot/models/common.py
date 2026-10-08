from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

_BASE58_ALPHABET_TEXT = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_ALPHABET = frozenset(_BASE58_ALPHABET_TEXT)
_BASE58_INDEX = {char: index for index, char in enumerate(_BASE58_ALPHABET_TEXT)}


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


AwareUtcDatetime = Annotated[datetime, AfterValidator(_normalize_utc)]
SolanaAddress = Annotated[
    str,
    StringConstraints(
        min_length=32,
        max_length=44,
        pattern=r"^[1-9A-HJ-NP-Za-km-z]+$",
        strip_whitespace=True,
    ),
]


def is_solana_address(value: str) -> bool:
    """Return whether a base58 string decodes to one 32-byte Solana public key."""
    if not 32 <= len(value) <= 44 or any(char not in _BASE58_ALPHABET for char in value):
        return False
    number = 0
    for char in value:
        number = (number * 58) + _BASE58_INDEX[char]
    payload_size = (number.bit_length() + 7) // 8
    leading_zeroes = len(value) - len(value.lstrip("1"))
    return leading_zeroes + payload_size == 32


class DataAvailability(StrEnum):
    AVAILABLE = "available"
    STALE = "stale"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class DataConfidence(StrEnum):
    EXACT_ONCHAIN = "exact_onchain"
    HIGH = "high"
    ESTIMATED = "estimated"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ProviderProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1, max_length=64)
    observed_at: AwareUtcDatetime
    received_at: AwareUtcDatetime | None = None
    confidence: DataConfidence = DataConfidence.UNKNOWN
    source_reference: str | None = Field(default=None, max_length=256)


class Observation[ValueT](BaseModel):
    """A value plus explicit availability and provenance.

    Unknown is never silently converted to zero. Stale values may retain their
    last observed value so consumers can decide whether to degrade or skip.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: ValueT | None = None
    availability: DataAvailability
    provenance: ProviderProvenance
    reason: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def validate_value_availability(self) -> Self:
        if self.availability == DataAvailability.AVAILABLE and self.value is None:
            raise ValueError("available observations require a value")
        if self.availability in {DataAvailability.UNKNOWN, DataAvailability.UNAVAILABLE}:
            if self.value is not None:
                raise ValueError("unknown or unavailable observations cannot carry a value")
            if not self.reason:
                raise ValueError("unknown or unavailable observations require a reason")
        return self
