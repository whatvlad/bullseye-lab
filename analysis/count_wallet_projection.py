import asyncio
import json
from sqlalchemy import select, func
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import WalletTradeObservationRecord

async def main():
    database = Database(create_database_engine(Settings().database_url))
    try:
        async with database.sessions() as session:
            count = await session.scalar(select(func.count()).select_from(WalletTradeObservationRecord))
            print(json.dumps({'wallet_observations': count}))
    finally:
        await database.dispose()

asyncio.run(main())
