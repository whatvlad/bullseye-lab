"""Two read-only RPC calls to distinguish chain timestamp age from receive lag."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from memebot.core.config import Settings
from memebot.providers.solana.rpc import JsonRpcSolanaClient
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import DomainEventRecord


async def main():
    settings = Settings()
    rpc = JsonRpcSolanaClient(str(settings.solana_rpc_http_url))
    db = Database(create_database_engine(settings.database_url))
    try:
        slot = await rpc._call("getSlot", [{"commitment": "confirmed"}])
        block_time = await rpc._call("getBlockTime", [slot])
        now = datetime.now(UTC)
        async with db.sessions() as session:
            rows = list(
                await session.scalars(
                    select(DomainEventRecord)
                    .where(
                        DomainEventRecord.provider == "solana_rpc_pump",
                        DomainEventRecord.event_type == "token.trade",
                    )
                    .order_by(DomainEventRecord.ingested_at.desc())
                    .limit(20)
                )
            )
        result = {
            "checked_at": now.isoformat(),
            "rpc_slot": slot,
            "block_time": block_time,
            "rpc_bank_timestamp_age_seconds": now.timestamp() - block_time,
            "latest_trade_ages": [
                {
                    "source_slot": row.source_slot,
                    "receipt_minus_source_seconds": (
                        row.provider_received_at - row.source_event_at
                    ).total_seconds(),
                    "ingest_minus_receipt_seconds": (
                        row.ingested_at - row.provider_received_at
                    ).total_seconds(),
                }
                for row in rows
            ],
        }
        await asyncio.to_thread(
            Path("analysis/chain_clock_20261006.json").write_text, json.dumps(result, indent=2)
        )
        print(json.dumps(result, indent=2))
    except Exception as error:
        print(json.dumps({"error_code": type(error).__name__}))
    finally:
        await rpc.close()
        await db.dispose()


asyncio.run(main())
