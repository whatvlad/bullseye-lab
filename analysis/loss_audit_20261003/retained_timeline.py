"""Indexed, bounded, read-only local event timelines around the 20 audited trades."""
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
from uuid import UUID
from sqlalchemy import select, text
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import TokenTradeRecord, DomainEventRecord

ROOT = Path(__file__).resolve().parent
LIMIT = 50000


async def main():
    settings = Settings(pumpportal_api_key=None)
    database = Database(create_database_engine(settings.database_url))
    reports = []
    try:
        async with database.sessions() as session, session.begin():
            await session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            await session.execute(text("SET LOCAL statement_timeout = '30s'"))
            for folder, label in [(ROOT/'current_1248', 'previous'), (ROOT/'current_1250', 'current')]:
                snapshot = json.loads((folder/'snapshot.json').read_text(encoding='utf-8'))
                for position in snapshot['outcomes']:
                    start = datetime.fromisoformat(position['entry_at'])
                    end = datetime.fromisoformat(position['exit_at'])
                    rows = (await session.execute(select(
                        TokenTradeRecord.event_id, TokenTradeRecord.source_event_at,
                        TokenTradeRecord.source_slot, TokenTradeRecord.side,
                        TokenTradeRecord.quote_amount_raw, TokenTradeRecord.token_amount_raw,
                        TokenTradeRecord.virtual_quote_reserves, TokenTradeRecord.virtual_token_reserves,
                        DomainEventRecord.provider_received_at, DomainEventRecord.ingested_at,
                        DomainEventRecord.payload['normalized_state'].label('normalized_state'),
                    ).join(DomainEventRecord, DomainEventRecord.event_id == TokenTradeRecord.event_id)
                      .where(TokenTradeRecord.token_id == UUID(position['token_id']),
                             TokenTradeRecord.source_event_at >= start-timedelta(seconds=5),
                             TokenTradeRecord.source_event_at <= end+timedelta(seconds=2))
                      .order_by(TokenTradeRecord.source_event_at, TokenTradeRecord.event_id)
                      .limit(LIMIT))).all()
                    reports.append({'cohort': label, 'mint': position['mint'], 'entry_at': start,
                                    'exit_at': end, 'record_limit_reached': len(rows) == LIMIT,
                                    'retained_events': [dict(row._mapping) for row in rows]})
        (ROOT/'retained_timelines.json').write_text(json.dumps({'timelines': reports}, indent=2, default=str), encoding='utf-8')
        print(json.dumps({'positions': len(reports), 'retained_trade_records': sum(len(row['retained_events']) for row in reports),
                          'any_truncation': any(row['record_limit_reached'] for row in reports)}))
    finally:
        await database.dispose()


asyncio.run(main())
