import asyncio

import pytest

from memebot.storage.database.write_behind import WriteBehindWriter


@pytest.mark.asyncio
async def test_batches_in_order_and_reports_written():
    stored = []

    async def store(batch):
        stored.append(list(batch))

    writer = WriteBehindWriter(store, max_batch=3, max_delay_seconds=0)
    task = asyncio.create_task(writer.run())
    try:
        for item in range(7):
            writer.submit(item)
        assert await writer.flush(2)
        assert [item for batch in stored for item in batch] == list(range(7))
        assert max(len(batch) for batch in stored) <= 3
        assert writer.pending == 0 and writer.written == 7
    finally:
        task.cancel()


@pytest.mark.asyncio
async def test_failed_batch_is_retried_not_dropped():
    calls = []

    async def store(batch):
        calls.append(list(batch))
        if len(calls) == 1:
            raise RuntimeError("database down")

    writer = WriteBehindWriter(store, max_delay_seconds=0, retry_seconds=0)
    task = asyncio.create_task(writer.run())
    try:
        writer.submit("trade")
        assert await writer.flush(2)
        assert calls == [["trade"], ["trade"]] and writer.metrics["failures"] == 1
    finally:
        task.cancel()


@pytest.mark.asyncio
async def test_wait_written_times_out_while_store_is_blocked():
    release = asyncio.Event()

    async def store(batch):
        await release.wait()

    writer = WriteBehindWriter(store, max_delay_seconds=0)
    task = asyncio.create_task(writer.run())
    try:
        sequence = writer.submit("trade")
        assert not await writer.wait_written(sequence, 0.05)
        release.set()
        assert await writer.wait_written(sequence, 2)
    finally:
        task.cancel()


@pytest.mark.asyncio
async def test_registry_batch_stores_trades_and_falls_back_on_duplicates():
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy import func, select

    from memebot.storage.database.engine import Database, create_database_engine
    from memebot.storage.database.models import TokenTradeRecord
    from memebot.storage.database.outcomes import OutcomeRecorder
    from memebot.storage.database.registry import TokenRegistry
    from test_phase7_outcomes import _discovery, _trade

    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    try:
        registry = TokenRegistry(
            database.sessions, outcome_recorder=OutcomeRecorder(database.sessions)
        )
        await registry.handle(_discovery())
        trades = [_trade(UUID(int=100 + i), i, Decimal(2)) for i in range(5)]
        await registry.handle_many(trades[:3])
        # A batch containing an already-stored event must still store the new ones.
        await registry.handle_many(trades[2:])
        async with database.sessions() as session:
            count = await session.scalar(select(func.count()).select_from(TokenTradeRecord))
        assert count == 5
    finally:
        await database.dispose()
