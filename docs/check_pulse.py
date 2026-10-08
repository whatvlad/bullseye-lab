"""Read-only Pulse query/renderer check, without sending Telegram messages."""
import asyncio
import json

from memebot.core.config import Settings
from memebot.providers.price.coingecko import CoinGeckoQuotePriceProvider
from memebot.pulse.service import PulseService
from memebot.pulse.views import pulse_view
from memebot.storage.database.engine import Database, create_database_engine


async def main():
    settings = Settings()
    database = Database(create_database_engine(settings.database_url))
    prices = CoinGeckoQuotePriceProvider(str(settings.coingecko_base_url))
    try:
        payload = await PulseService(database.sessions, settings, prices).snapshot()
        print(json.dumps({"view": pulse_view(payload)}, ensure_ascii=True))
    finally:
        await prices.close()
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
