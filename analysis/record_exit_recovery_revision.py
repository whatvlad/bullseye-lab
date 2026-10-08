"""Record the authorized code revision without resetting PAPER balances/exposure."""
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
    assert settings.execution_mode == 'paper' and not settings.ollama_model
    assert settings.telegram_bot_token and settings.telegram_allowed_user_ids
    summary = settings.safe_summary()
    summary.pop('database_url', None)
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
            before = deepcopy(snapshot)
            Path('analysis/pre_migration_fix_experiment_snapshot.json').write_text(
                json.dumps(before, indent=2), encoding='utf-8')
            at = utc_now().isoformat()
            snapshot.setdefault('configuration_history', []).append({
                'superseded_at': at, 'reason': 'User requested Telegram restoration and migration exit repair',
                'captured_at': before['captured_at'], 'settings': before['settings'],
                'trading_control': before['trading_control'], 'strategy': before['strategy']})
            snapshot['captured_at'] = at
            snapshot['settings'] = summary
            run.configuration_snapshot_json = snapshot
            run.notes = (run.notes or '') + '\n' + at + ': Telegram restored; canonical atomic migration SELL recovery. Strategy/risk thresholds unchanged. Existing exposure and history retained.'
            print(json.dumps({'revision_recorded': True, 'portfolio_id': str(run.portfolio_id),
                              'thresholds_changed': False}))
    finally:
        await db.dispose()


asyncio.run(main())
