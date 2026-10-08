"""Explicitly preserve the previous configuration before the authorized UI revision."""
import asyncio
import json
from copy import deepcopy
from pathlib import Path

from sqlalchemy import select

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import ExperimentRunRecord, TradingControlRecord


async def main():
    settings = Settings(pumpportal_api_key=None)
    summary = settings.safe_summary()
    summary.pop('database_url', None)
    assert settings.execution_mode == 'paper' and not settings.ollama_model
    db = Database(create_database_engine(settings.database_url))
    try:
        async with db.sessions() as session, session.begin():
            control = await session.get(TradingControlRecord, 1)
            assert control and control.entries_paused
            run = await session.scalar(select(ExperimentRunRecord).where(
                ExperimentRunRecord.status == 'active').with_for_update())
            assert run and run.name == 'standard-pump-operational-paper-20261002-233007'
            snapshot = deepcopy(run.configuration_snapshot_json)
            assert snapshot['settings']['execution_parameters'] == summary['execution_parameters']
            previous = deepcopy(snapshot)
            Path('analysis/pre_telegram_history_snapshot.json').write_text(json.dumps(previous, indent=2), encoding='utf-8')
            at = utc_now().isoformat()
            snapshot.setdefault('configuration_history', []).append(dict(
                superseded_at=at, reason='User requested full coin identity and complete Telegram PAPER history',
                captured_at=previous['captured_at'], settings=previous['settings'],
                trading_control=previous['trading_control'], strategy=previous['strategy']))
            snapshot['settings'] = summary
            snapshot['captured_at'] = at
            run.configuration_snapshot_json = snapshot
            run.notes = (run.notes or '') + '\n' + at + ': Telegram full mint/name, paginated history and ZIP/CSV export. Execution settings and thresholds unchanged.'
            print(json.dumps({'revision_recorded': True, 'portfolio_id': str(run.portfolio_id)}))
    finally:
        await db.dispose()


asyncio.run(main())
