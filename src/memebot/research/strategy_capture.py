"""Read-only, reproducible strategy evidence export. Never starts a worker."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from sqlalchemy import text

from memebot.core.config import Settings
from memebot.storage.database.engine import create_database_engine

QUERIES = {
    "tokens": "SELECT id,mint,name,symbol,creator,first_seen_at,source_created_at,"
    "launch_venue FROM tokens WHERE id IN (SELECT token_id FROM token_trades UNION "
    "SELECT token_id FROM strategy_decisions UNION SELECT token_id FROM paper_positions)",
    "market_trades": "SELECT t.*,d.ingested_at,d.provider,d.provider_received_at "
    "FROM token_trades t JOIN domain_events d USING(event_id) "
    "ORDER BY t.token_id,d.ingested_at,t.event_id",
    "features": "SELECT f.*,d.ingested_at,d.provider FROM market_feature_snapshots f "
    "JOIN domain_events d USING(event_id) ORDER BY f.token_id,d.ingested_at,f.event_id",
    "decisions": "SELECT s.*,d.ingested_at FROM strategy_decisions s "
    "JOIN domain_events d USING(event_id) ORDER BY s.token_id,d.ingested_at,s.event_id",
    "decision_outcomes": "SELECT * FROM decision_outcomes ORDER BY token_id,decided_at",
    "positions": "SELECT * FROM paper_positions ORDER BY opened_at",
    "trade_outcomes": "SELECT * FROM trade_outcomes ORDER BY entry_at",
    "orders": "SELECT * FROM paper_orders ORDER BY created_at",
    "portfolios": "SELECT * FROM paper_portfolios",
    "strategies": "SELECT * FROM strategy_configurations",
    "experiments": "SELECT * FROM experiment_runs",
    "health": "SELECT ingested_at,provider,payload->>'state' state,"
    "payload->>'error_code' error_code FROM domain_events "
    "WHERE event_type='provider.health_updated' ORDER BY ingested_at",
}


async def capture(destination: Path) -> dict[str, object]:
    await asyncio.to_thread(destination.mkdir, parents=True, exist_ok=False)
    engine = create_database_engine(Settings().database_url)
    manifest: dict[str, object] = {}
    try:
        async with engine.connect() as connection:
            await connection.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
            await connection.execute(text("SET LOCAL statement_timeout = '120s'"))
            manifest["database_time_utc"] = str(
                (await connection.execute(text("SELECT now()"))).scalar()
            )
            manifest["total_discovered_tokens"] = (
                await connection.execute(text("SELECT count(*) FROM tokens"))
            ).scalar()
            for name, query in QUERIES.items():
                count = 0
                digest = hashlib.sha256()
                rows = await connection.stream(text(query))
                with (destination / f"{name}.jsonl").open("wb") as output:
                    async for row in rows.mappings():
                        line = (json.dumps(dict(row), default=str, sort_keys=True) + "\n").encode()
                        output.write(line)
                        digest.update(line)
                        count += 1
                manifest[name] = {"rows": count, "sha256": digest.hexdigest()}
                print(json.dumps({"exported": name, "rows": count}), flush=True)
    finally:
        await engine.dispose()
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        asyncio.run(capture(args.output))
    except Exception as error:
        parser.exit(1, f"Read-only export failed: {type(error).__name__}\n")


if __name__ == "__main__":
    main()
