"""Read-only: export social links from tokens.metadata_json for dataset tokens."""
import asyncio
import json
import sys

from sqlalchemy import text

from memebot.core.config import Settings
from memebot.storage.database.engine import create_database_engine


async def main():
    engine = create_database_engine(Settings(pumpportal_api_key=None).database_url)
    async with engine.connect() as conn:
        sample = (await conn.execute(text(
            "select metadata_json from tokens where metadata_json is not null "
            "order by last_seen_at desc limit 3"))).scalars().all()
        rows = (await conn.execute(text(
            "select id::text, name, symbol, metadata_json from tokens where id in "
            "(select distinct token_id from token_trades where source_event_at >= '2026-10-02')"))).all()
    await engine.dispose()
    print("sample keys:", [sorted((m or {}).keys())[:30] for m in sample])
    print(json.dumps(sample[0], default=str)[:1500])
    out = {r[0]: {"name": r[1], "symbol": r[2], "meta": r[3]} for r in rows}
    json.dump(out, open(sys.argv[1], "w"), default=str)
    print("tokens", len(out), "with metadata", sum(1 for v in out.values() if v["meta"]))


asyncio.run(main())
