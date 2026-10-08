"""Bounded operational ingestion validation; entries and all orders disabled."""

import argparse
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from memebot.apps.worker import run_discovery_worker
from memebot.core.config import Settings
from memebot.core.logging import configure_logging
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import DomainEventRecord, PaperOrderRecord, PaperPositionRecord

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--seconds", type=int, default=180)
parser.add_argument("--output", default="operational_stream_validation.json")
args = parser.parse_args()
assert 1 <= args.seconds <= 1800
assert Path(args.output).name == args.output


async def main():
    settings = Settings(
        pumpportal_api_key=None,
        paper_trading_enabled=False,
        telegram_trade_notifications_enabled=False,
        telegram_tracked_wallet_notifications_enabled=False,
    )
    assert settings.execution_mode == "paper"
    db = Database(create_database_engine(settings.database_url))
    control = await ControlRepository(db.sessions).get()
    assert control.entries_paused, "Validation requires entries already paused"
    async with db.sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(PaperPositionRecord)
                .where(PaperPositionRecord.status == "open")
            )
            == 0
        )
        orders_before = await session.scalar(select(func.count()).select_from(PaperOrderRecord))
    start = datetime.now(UTC)
    configure_logging("INFO", "json")
    try:
        await run_discovery_worker(settings, run_seconds=args.seconds)
        end = datetime.now(UTC)
        async with db.sessions() as session:
            rows = list(
                await session.scalars(
                    select(DomainEventRecord).where(
                        DomainEventRecord.provider == "solana_rpc_pump",
                        DomainEventRecord.ingested_at >= start,
                        DomainEventRecord.ingested_at <= end,
                    )
                )
            )
            orders_after = await session.scalar(select(func.count()).select_from(PaperOrderRecord))
        assert orders_before == orders_after
        trades = [r.payload for r in rows if r.event_type == "token.trade"]
        states = [t.get("normalized_state") or {} for t in trades]
        result = {
            "started_at": start,
            "ended_at": end,
            "orders_added": orders_after - orders_before,
            "events": dict(Counter(r.event_type for r in rows)),
            "continuity": dict(Counter(s.get("continuity_status") for s in states)),
            "state_reasons": dict(
                Counter(s.get("invalidation_reason") or s.get("reason") for s in states)
            ),
            "degraded": dict(
                Counter(
                    r.payload.get("error_code")
                    for r in rows
                    if r.event_type == "provider.health_updated"
                    and r.payload.get("state") == "degraded"
                )
            ),
        }
        (ROOT / "analysis" / args.output).write_text(json.dumps(result, indent=2, default=str))
        print(json.dumps(result, default=str))
    finally:
        await db.dispose()


asyncio.run(main())
