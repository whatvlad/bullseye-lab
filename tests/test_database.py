from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from memebot.events.models import TokenDiscovered
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import DomainEventRecord, TokenRecord

MINT = "So11111111111111111111111111111111111111112"


@pytest.mark.asyncio
async def test_async_database_persists_token_and_reproducible_event() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    event = TokenDiscovered(
        provider="test",
        source_event_at=datetime(2026, 8, 22, 18, 0, tzinfo=UTC),
        mint=MINT,
        name="Research Coin",
    )
    async with database.sessions.begin() as session:
        session.add(TokenRecord(mint=MINT, name="Research Coin"))
        session.add(
            DomainEventRecord(
                event_id=event.event_id,
                event_type=event.event_type.value,
                schema_version=event.schema_version,
                provider=event.provider,
                source_event_at=event.source_event_at,
                provider_received_at=event.provider_received_at,
                ingested_at=event.ingested_at,
                correlation_id=event.correlation_id,
                source_sequence=event.source_sequence,
                payload=event.model_dump(mode="json"),
            )
        )

    async with database.sessions() as session:
        token = (await session.execute(select(TokenRecord))).scalar_one()
        stored_event = (await session.execute(select(DomainEventRecord))).scalar_one()

    assert token.mint == MINT
    assert stored_event.event_id == event.event_id
    assert stored_event.payload["mint"] == MINT
    await database.dispose()
