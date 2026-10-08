from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from memebot.events.models import TokenRiskAssessed
from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.risk import RiskEvidence, RiskResult
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import TokenRiskAssessmentRecord
from memebot.storage.database.registry import TokenRegistry

MINT = "So11111111111111111111111111111111111111112"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
NOW = datetime(2026, 8, 22, 22, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_risk_assessment_reasons_and_evidence_are_persisted() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    provenance = ProviderProvenance(
        provider="solana_rpc",
        observed_at=NOW,
        confidence=DataConfidence.EXACT_ONCHAIN,
        source_reference="slot:700",
    )
    event = TokenRiskAssessed(
        event_id=UUID(int=201),
        provider="bullseye_risk_engine",
        source_event_at=NOW,
        source_slot=700,
        mint=MINT,
        market=MARKET,
        trigger_event_id=UUID(int=200),
        result=RiskResult(
            allowed=False,
            risk_score=Decimal("75"),
            data_completeness_percent=Decimal("90"),
            hard_reject_reasons=("freeze_authority_enabled",),
            warnings=("top5_holder_concentration",),
            evidence=(
                RiskEvidence(
                    code="freeze_authority_enabled",
                    category="mint",
                    message="Freeze authority is still enabled",
                    value=True,
                    severity="hard_reject",
                    provenance=provenance,
                ),
            ),
        ),
    )

    assert await registry.handle(event) is True
    assert await registry.handle(event) is False

    async with database.sessions() as session:
        count = await session.scalar(select(func.count()).select_from(TokenRiskAssessmentRecord))
    queried = await registry.latest_risk(MINT)
    inspected = await registry.inspect_token(MINT)

    assert count == 1
    assert queried[0]["hard_reject_reasons"] == ["freeze_authority_enabled"]
    assert queried[0]["evidence"][0]["value"] is True
    assert inspected is not None
    assert inspected["latest_risk_assessment"]["allowed"] is False
    await database.dispose()
