"""Read-only check of Telegram pages and full history export against the real DB."""
import asyncio
import csv
import io
import json
import zipfile
from pathlib import Path

from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.paper_history import PaperHistoryRepository
from memebot.telegram.history import detail_view, history_view


async def main():
    db = Database(create_database_engine(Settings().database_url))
    try:
        repo = PaperHistoryRepository(db.sessions)
        first = await repo.page()
        seen = []
        max_length = 0
        aww = None
        for page in range(first['pages']):
            payload = await repo.page(page)
            max_length = max(max_length, len(history_view(payload).encode('utf-16-le')) // 2)
            for item in payload['items']:
                seen.append(item['id'])
                detail = await repo.detail(item['id'])
                assert detail and detail['total'] >= 1
                max_length = max(max_length, len(detail_view(detail).encode('utf-16-le')) // 2)
                if item['mint'] == '9cxR58NxPER4oemD83iVZU9cKH54NdhzbeNfosJkpump':
                    aww = dict(name=item['name'], status=item['status'], pnl=item['realized_pnl'],
                               filled_orders=detail['total'])
        assert len(seen) == len(set(seen)) == first['total']
        assert max_length < 4096
        archive = await repo.archive()
        Path('analysis/bullseye_paper_history.zip').write_bytes(archive)
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            orders = list(csv.DictReader(io.StringIO(zipped.read('orders.csv').decode('utf-8-sig'))))
            positions = list(csv.DictReader(io.StringIO(zipped.read('positions.csv').decode('utf-8-sig'))))
        assert len(positions) == first['total']
        print(json.dumps(dict(positions=first['total'], pages=first['pages'], export_orders=len(orders),
            export_bytes=len(archive), max_message_units=max_length, aww=aww), ensure_ascii=False))
    finally:
        await db.dispose()


asyncio.run(main())
