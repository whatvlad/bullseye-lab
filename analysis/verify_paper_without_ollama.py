"""Read-only verification of the PAPER restart against the retained baseline."""
import asyncio
import json
from pathlib import Path

from memebot.core.config import Settings
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository


async def main():
    settings = Settings(pumpportal_api_key=None, telegram_bot_token=None)
    db = Database(create_database_engine(settings.database_url))
    try:
        repo = ExperimentRepository(db.sessions)
        runs = await repo.list(limit=10)
        baseline = next(run for run in runs if run['name'] ==
                        'standard-pump-operational-paper-20261002-214954')
        active = await repo.active()
        assert active is not None and active['id'] != baseline['id']
        old = baseline['configuration_snapshot']['settings']['execution_parameters']
        new = active['configuration_snapshot']['settings']['execution_parameters']
        changes = [key for key in set(old) | set(new) if old.get(key) != new.get(key)]
        assert changes == ['ollama_model'], changes
        assert not new['ollama_model'] and not settings.ollama_model
        control = await ControlRepository(db.sessions).get()
        assert control is not None and not control.entries_paused
        assert active['strategy_version_id'] == baseline['strategy_version_id']
        assert active['configuration_snapshot']['trading_control'] == baseline['configuration_snapshot']['trading_control']
        print(json.dumps({'active_experiment': active['name'], 'ollama_enabled': False,
                          'changed_execution_parameters': changes,
                          'strategy_version_unchanged': True, 'entries_paused': False}))
    finally:
        await db.dispose()


asyncio.run(main())
