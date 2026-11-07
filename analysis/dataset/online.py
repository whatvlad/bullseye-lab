"""Read-only: per-minute trade counts since Oct 2 (online detection) and token creation times."""
import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import text

from memebot.core.config import Settings
from memebot.storage.database.engine import create_database_engine

SINCE = datetime(2026, 10, 2, tzinfo=UTC)


async def main():
    engine = create_database_engine(Settings(pumpportal_api_key=None).database_url)
    async with engine.connect() as conn:
        minutes = (await conn.execute(text(
            "select extract(epoch from date_trunc('minute', source_event_at))::bigint, count(*) "
            "from token_trades where source_event_at >= :s group by 1 order by 1"), {"s": SINCE})).all()
        created = (await conn.execute(text(
            "select t.id::text, extract(epoch from coalesce(t.source_created_at, t.first_seen_at)) "
            "from tokens t where t.id in (select distinct token_id from token_trades where source_event_at >= :s)"),
            {"s": SINCE})).all()
    await engine.dispose()
    json.dump({"minutes": [[int(a), int(b)] for a, b in minutes],
               "created": {a: float(b) for a, b in created}}, open("data/online.json", "w"))
    counts = [b for _, b in minutes]
    print("online minutes", len(counts), "median trades/min", sorted(counts)[len(counts) // 2],
          "tokens", len(created))
    # segments: consecutive minutes
    segs, start, prev = [], None, None
    for m, _ in minutes:
        if prev is None or m - prev > 60:
            if start is not None:
                segs.append((start, prev))
            start = m
        prev = m
    segs.append((start, prev))
    long = [(a, b) for a, b in segs if b - a >= 3600]
    print("segments", len(segs), ">=1h", len(long), "hours in >=1h segments",
          round(sum(b - a for a, b in long) / 3600, 1))
    for a, b in long:
        print(datetime.fromtimestamp(a, UTC).strftime("%m-%d %H:%M"), "->",
              datetime.fromtimestamp(b, UTC).strftime("%m-%d %H:%M"), round((b - a) / 3600, 1), "h")


asyncio.run(main())
