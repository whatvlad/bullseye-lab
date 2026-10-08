"""Read-only replay of the redundant per-tick feature work on retained trades."""

import asyncio
import json
from pathlib import Path
from time import perf_counter

from sqlalchemy import select

from memebot.core.config import Settings
from memebot.events.models import TokenTrade, parse_core_event
from memebot.intelligence.features.engine import RollingFeatureEngine
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import DomainEventRecord


async def main():
    settings = Settings()
    db = Database(create_database_engine(settings.database_url))
    try:
        async with db.sessions() as session:
            rows = list(
                await session.scalars(
                    select(DomainEventRecord.payload)
                    .where(
                        DomainEventRecord.provider == "solana_rpc_pump",
                        DomainEventRecord.event_type == "token.trade",
                    )
                    .order_by(DomainEventRecord.ingested_at.desc())
                    .limit(3000)
                )
            )
    finally:
        await db.dispose()
    trades = [parse_core_event(row) for row in reversed(rows)]
    results = {}
    snapshot_counts = []
    emitted = []
    for mode in ("prior_no_position_path", "corrected_no_position_path"):
        engine = RollingFeatureEngine(settings.feature_windows_seconds)
        snapshots = 0
        mode_snapshots = []
        started = perf_counter()
        for trade in trades:
            assert isinstance(trade, TokenTrade)
            snapshot = engine.ingest_trade(trade)
            snapshots += snapshot is not None
            if snapshot is not None:
                mode_snapshots.append(snapshot)
            if snapshot is None and mode == "prior_no_position_path":
                engine.current_snapshot(trade)
        results[mode] = perf_counter() - started
        snapshot_counts.append(snapshots)
        emitted.append(mode_snapshots)
    assert snapshot_counts[0] == snapshot_counts[1]
    assert [s.model_dump(exclude={"ingested_at"}) for s in emitted[0]] == [
        s.model_dump(exclude={"ingested_at"}) for s in emitted[1]
    ]
    report = {
        "trades": len(trades),
        "strategy_snapshots_unchanged": snapshot_counts,
        "strategy_snapshot_contents_identical": True,
        "seconds": results,
        "scope": "retained replay; no DB writes, RPC, orders or change to entry snapshots",
    }
    await asyncio.to_thread(
        Path("analysis/feature_work_benchmark_20261006.json").write_text,
        json.dumps(report, indent=2),
    )
    print(json.dumps(report, indent=2))


asyncio.run(main())
