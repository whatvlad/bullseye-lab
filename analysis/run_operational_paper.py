"""Bounded use of the existing PAPER worker; never creates live orders."""
import asyncio
import argparse
import json
from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from memebot.apps.worker import run_discovery_worker
from memebot.core.config import Settings
from memebot.core.logging import configure_logging
from memebot.core.instance import InstanceAlreadyRunning
from memebot.core.fingerprint import experiment_matches
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.models import PaperPositionRecord

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'analysis/paper_run_state.json'


async def main(run_seconds: float | None = 900, *, resume_existing: bool = False):
    settings = Settings(pumpportal_api_key=None)
    assert settings.execution_mode == 'paper' and settings.paper_trading_enabled
    configure_logging('INFO', 'json')
    db = Database(create_database_engine(settings.database_url))
    controls = ControlRepository(db.sessions)
    experiments = ExperimentRepository(db.sessions)
    state = {'status': 'starting', 'bounded_seconds': run_seconds, 'target_completed': 100,
             'started_at': datetime.now(UTC).isoformat(), 'provider': 'native Pump.fun',
             'live_enabled': False, 'thresholds_changed': False}

    def save():
        STATE.write_text(json.dumps(state, indent=2, default=str), encoding='utf-8')

    async def ready():
        await controls.set_paused(True, user_id=0)
        old = await experiments.active()
        if resume_existing:
            if not old or not experiment_matches(old, settings.safe_summary(), await controls.get()):
                raise RuntimeError('Existing PAPER run configuration must be explicitly reconciled before resuming')
            state.update(status='observing', experiment_name=old['name'], portfolio_id=old['portfolio_id'],
                         observation_started_at=old['started_at'], strategy=old['strategy_key'],
                         initial_cash=str(settings.starting_capital))
            save()
            print(json.dumps({'paper_run': 'resumed', 'name': old['name'], 'entries_paused': True}), flush=True)
            return
        if old:
            await experiments.stop()  # Refuses to stop an experiment with open exposure.
        control = await controls.get()
        assert control is not None
        summary = settings.safe_summary()
        summary.pop('database_url', None)
        exp = await experiments.start(
            name='standard-pump-operational-paper-' + datetime.now(UTC).strftime('%Y%m%d-%H%M%S'),
            initial_cash=settings.starting_capital,
            currency=settings.starting_capital_currency,
            settings_snapshot=summary,
            notes=f'PAPER run duration: {run_seconds if run_seconds is not None else "continuous"}. Native discovery explicitly approved. '
                  'Current atomic canonical execution; unchanged strategy and risk thresholds.',
        )
        state.update(status='observing', experiment_name=exp['name'],
                     portfolio_id=exp['portfolio_id'], observation_started_at=exp['started_at'],
                     strategy=control.active_strategy_key, initial_cash=str(settings.starting_capital))
        save()
        await controls.set_paused(False, user_id=0)
        print(json.dumps({'paper_run': 'observing', 'name': exp['name']}, default=str), flush=True)

    instance_conflict = False
    try:
        async with asyncio.timeout(run_seconds + 300 if run_seconds is not None else None):
            await run_discovery_worker(settings, run_seconds=run_seconds, on_ready=ready)
        state['status'] = 'observation_complete'
    except InstanceAlreadyRunning:
        instance_conflict = True
        print('PAPER/discovery is already running. Existing worker and entry controls unchanged.')
    except asyncio.CancelledError:
        state['status'] = 'interrupted'
        raise
    except Exception as exc:
        state.update(status='failed', error_type=type(exc).__name__)
        # Error text can contain provider URLs; retain only its class here.
        raise
    finally:
        if not instance_conflict:
            await controls.set_paused(True, user_id=0)
            if state.get('portfolio_id'):
                from uuid import UUID
                async with db.sessions() as session:
                    open_rows = list(await session.scalars(select(PaperPositionRecord).where(
                        PaperPositionRecord.portfolio_id == UUID(state['portfolio_id']),
                        PaperPositionRecord.status == 'open')))
                state['open_positions_at_stop'] = len(open_rows)
                if not open_rows:
                    await experiments.stop()
            state['ended_at'] = datetime.now(UTC).isoformat()
            save()
        await db.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start native-discovery PAPER trading with an isolated experiment.')
    duration = parser.add_mutually_exclusive_group()
    duration.add_argument('--continuous', action='store_true', help='Run until Ctrl+C')
    duration.add_argument('--run-seconds', type=float, default=900, help='Bounded duration; default 900')
    parser.add_argument('--resume-existing', action='store_true', help='Resume the active portfolio; keep entries paused for review')
    args = parser.parse_args()
    if args.run_seconds <= 0:
        parser.error('--run-seconds must be positive')
    try:
        asyncio.run(main(None if args.continuous else args.run_seconds, resume_existing=args.resume_existing))
    except KeyboardInterrupt:
        print('PAPER worker stopped; entries paused. Check any remaining open positions.')
