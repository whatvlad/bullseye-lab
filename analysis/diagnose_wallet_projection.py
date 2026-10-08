import asyncio
import json
import re
from sqlalchemy.exc import DBAPIError
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.wallets import WalletIntelligenceRepository

async def main():
    database = Database(create_database_engine(Settings().database_url))
    try:
        repository = WalletIntelligenceRepository(database.sessions)
        for stage in ('backfill', 'terminal'):
            try:
                count = (await repository.backfill_existing(limit=1) if stage == 'backfill'
                         else await repository.reconcile_terminal_lifecycles(limit=1))
                print(json.dumps({'stage': stage, 'processed': count}))
            except DBAPIError as error:
                original = error.orig
                fields = [(name, str(error.params[int(number)-1])) for name, number in re.findall(r'([a-z_]+)=\$(\d+)', error.statement or '') if name in ('mfe_percent', 'mae_percent', 'realized_return_percent')]
                print(json.dumps({'percentage_fields': fields}))
                print(json.dumps({'stage': stage, 'type': type(original).__name__,
                    'sqlstate': getattr(original, 'sqlstate', None),
                    'cause_type': type(getattr(original, '__cause__', None)).__name__,
                    'message': str(original).split('\n')[0][:250]}))
    finally:
        await database.dispose()

asyncio.run(main())

