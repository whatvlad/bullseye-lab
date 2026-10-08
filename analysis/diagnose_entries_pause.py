import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime
from sqlalchemy import select
from memebot.core.config import Settings
from memebot.core.fingerprint import experiment_matches
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.registry import TokenRegistry
from memebot.storage.database.models import TradingControlRecord, ProviderHealthRecord, PaperOrderRecord

async def main():
    settings = Settings(pumpportal_api_key=None)
    database = Database(create_database_engine(settings.database_url))
    try:
        control = await ControlRepository(database.sessions).get()
        experiment = await ExperimentRepository(database.sessions).active()
        summary = settings.safe_summary()
        expected = experiment['configuration_snapshot'] if experiment else {}
        state = await TokenRegistry(database.sessions).paper_risk_snapshot('', as_of=datetime.now(UTC))
        result = {'checked_at': datetime.now(UTC).isoformat(),
            'entries_paused': control.entries_paused if control else None,
            'experiment_active': bool(experiment),
            'experiment_matches': experiment_matches(experiment, summary, control),
            'code_matches': expected.get('settings', {}).get('code_fingerprint') == summary.get('code_fingerprint'),
            'parameter_diff_keys': [key for key in set(expected.get('settings', {}).get('execution_parameters', {})) | set(summary.get('execution_parameters', {}))
                if expected.get('settings', {}).get('execution_parameters', {}).get(key) != summary.get('execution_parameters', {}).get(key)],
            'control_differences': {key: {'expected': str(expected.get('trading_control', {}).get(key)), 'actual': str(value)}
                for key, value in asdict(control).items() if key != 'entries_paused' and str(expected.get('trading_control', {}).get(key)) != str(value)} if control else {},
            'daily_loss_limit_percent': str(settings.paper_daily_loss_limit_percent),
            'risk': {key: str(value) for key, value in asdict(state).items()} if state else None}
        async with database.sessions() as session:
            row = await session.get(TradingControlRecord, 1)
            result['pause_updated_at'] = str(row.updated_at)
            result['last_change_origin'] = 'system_safety' if row.updated_by_telegram_user_id is None else 'startup_or_cli' if row.updated_by_telegram_user_id == 0 else 'telegram_operator'
            rows = (await session.scalars(select(PaperOrderRecord).order_by(PaperOrderRecord.created_at.desc()).limit(8))).all()
            result['recent_orders'] = [{'at': str(row.created_at), 'status': row.status, 'reason': row.rejection_reason} for row in rows]
            health = (await session.scalars(select(ProviderHealthRecord))).all()
            result['provider_health'] = [{'provider': row.provider, 'state': row.state} for row in health]
        print(json.dumps(result, default=str))
    finally:
        await database.dispose()

asyncio.run(main())
