import asyncio
import json

from aiogram import Bot
from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.core.fingerprint import experiment_matches
from memebot.paper.risk_governor import PortfolioRiskGovernor
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.registry import TokenRegistry


async def main():
    settings = Settings(pumpportal_api_key=None)
    db = Database(create_database_engine(settings.database_url))
    bot = Bot(settings.telegram_bot_token.get_secret_value())
    try:
        commands = [command.command for command in await bot.get_my_commands()]
        assert 'history' in commands
        controls = ControlRepository(db.sessions)
        run = await ExperimentRepository(db.sessions).active()
        assert experiment_matches(run, settings.safe_summary(), await controls.get())
        assert settings.execution_mode == 'paper' and not settings.ollama_model
        blocked = await PortfolioRiskGovernor(settings, TokenRegistry(db.sessions)).daily_loss_limit_reached(as_of=utc_now())
        await controls.set_paused(blocked, user_id=0)
        print(json.dumps({'telegram_history_command_installed': True, 'active_portfolio': run['portfolio_id'],
            'entries_paused': blocked, 'thresholds_changed': False, 'ollama_enabled': False}))
    finally:
        await bot.session.close()
        await db.dispose()


asyncio.run(main())
