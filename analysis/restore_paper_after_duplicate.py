"""Restore the known active PAPER run after a rejected duplicate launcher."""
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
        active = await ExperimentRepository(db.sessions).active()
        assert active and active['name'] == 'standard-pump-operational-paper-20261002-233007'
        snapshot = active['configuration_snapshot']['settings']
        current = settings.safe_summary()
        assert snapshot['code_fingerprint'] == current['code_fingerprint']
        assert snapshot['execution_parameters'] == current['execution_parameters']
        assert not settings.ollama_model and settings.execution_mode == 'paper'
        state = dict(status='observing', bounded_seconds=None, target_completed=100,
                     started_at='2026-10-02T23:30:01.504728+00:00', provider='native Pump.fun',
                     live_enabled=False, thresholds_changed=False, experiment_name=active['name'],
                     portfolio_id=active['portfolio_id'], observation_started_at=active['started_at'],
                     strategy=active['strategy_key'], initial_cash=str(settings.starting_capital))
        Path('analysis/paper_run_state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
        await ControlRepository(db.sessions).set_paused(False, user_id=0)
        print(json.dumps({'status_restored': True, 'entries_paused': False}))
    finally:
        await db.dispose()


asyncio.run(main())
