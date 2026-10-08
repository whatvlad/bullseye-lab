from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, text

from memebot.core.config import Settings
from memebot.events.models import parse_core_event
from memebot.storage.database.engine import create_database_engine
from memebot.storage.database.models import DomainEventRecord, StrategyConfigurationRecord


async def export_session(destination: Path, end: datetime, mints: list[str] | None = None) -> int:
    if end.tzinfo is None:
        raise ValueError("end must be timezone-aware")
    await asyncio.to_thread(destination.mkdir, parents=True, exist_ok=False)
    engine = create_database_engine(Settings().database_url)
    count = 0
    try:
        async with engine.connect() as connection:
            await connection.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
            await connection.execute(text("SET LOCAL statement_timeout = '60s'"))
            # Include warm-up history instead of erasing prior age/feature context.
            query = (
                select(DomainEventRecord.payload)
                .where(DomainEventRecord.ingested_at < end)
                .order_by(DomainEventRecord.ingested_at, DomainEventRecord.event_id)
            )
            if mints:
                query = query.where(DomainEventRecord.payload["mint"].as_string().in_(mints))
            rows = await connection.stream(query)
            with (destination / "events.jsonl").open("w", encoding="utf-8") as output:
                async for row in rows:
                    event = parse_core_event(row[0])
                    output.write(event.model_dump_json() + "\n")
                    count += 1
            configurations = (
                (await connection.execute(select(StrategyConfigurationRecord.configuration_json)))
                .scalars()
                .all()
            )
            # All historical versions, not automatically the replay configuration.
            (destination / "strategy_versions.json").write_text(
                json.dumps(list(configurations), sort_keys=True, indent=2), encoding="utf-8"
            )
        return count
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only PostgreSQL event export")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--end", type=datetime.fromisoformat, required=True)
    parser.add_argument(
        "--mint", action="append", help="optional causal history for selected mints"
    )
    args = parser.parse_args()
    try:
        count = asyncio.run(export_session(args.output, args.end, args.mint))
    except Exception as error:
        parser.exit(1, f"Export failed: {type(error).__name__}; no market APIs called.\n")
    print(json.dumps({"events": count, "output": str(args.output)}))


if __name__ == "__main__":
    main()
