from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from memebot.events.models import EventType, TokenDiscovered, parse_core_event
from memebot.models.common import (
    DataAvailability,
    DataConfidence,
    Observation,
    ProviderProvenance,
)
from memebot.models.market import LaunchVenue
from memebot.models.risk import RiskResult

MINT = "So11111111111111111111111111111111111111112"


def test_event_round_trip_preserves_discriminated_type() -> None:
    event = TokenDiscovered(
        provider="solana_rpc",
        source_event_at=datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
        mint=MINT,
        name="Research Coin",
        symbol="RCH",
        launch_venue=LaunchVenue.PUMP_FUN,
    )

    parsed = parse_core_event(event.model_dump(mode="json"))

    assert isinstance(parsed, TokenDiscovered)
    assert parsed.event_type == EventType.TOKEN_DISCOVERED
    assert parsed.event_id == event.event_id
    assert parsed.source_event_at.tzinfo is UTC


def test_naive_event_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        TokenDiscovered(
            provider="solana_rpc",
            source_event_at=datetime(2026, 8, 22, 18, 0),
            mint=MINT,
        )


def test_unknown_observation_requires_reason_and_no_value() -> None:
    provenance = ProviderProvenance(
        provider="birdeye",
        observed_at=datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
        confidence=DataConfidence.UNKNOWN,
    )

    observation = Observation[Decimal](
        availability=DataAvailability.UNKNOWN,
        provenance=provenance,
        reason="holder data not returned",
    )

    assert observation.value is None
    with pytest.raises(ValidationError):
        Observation[Decimal](
            value=Decimal("0"),
            availability=DataAvailability.UNKNOWN,
            provenance=provenance,
            reason="missing",
        )


def test_hard_reject_cannot_be_allowed() -> None:
    with pytest.raises(ValidationError, match="allowed=False"):
        RiskResult(allowed=True, hard_reject_reasons=("freeze_authority",))
