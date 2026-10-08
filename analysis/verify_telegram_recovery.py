"""Verify active PAPER/Telegram configuration and restore entries only within risk gates."""
import asyncio
import json
from pathlib import Path

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
    try:
        registry = TokenRegistry(db.sessions)
        controls = ControlRepository(db.sessions)
        run = await ExperimentRepository(db.sessions).active()
        assert experiment_matches(run, settings.safe_summary(), await controls.get())
        assert settings.execution_mode == 'paper' and not settings.ollama_model
        assert settings.telegram_bot_token and settings.telegram_allowed_user_ids
        daily_block = await PortfolioRiskGovernor(settings, registry).daily_loss_limit_reached(as_of=utc_now())
        await controls.set_paused(daily_block, user_id=0)
        portfolio = await registry.paper_portfolio_report()
        risk = await registry.paper_risk_snapshot('', as_of=utc_now())
        result = dict(verified_at=utc_now().isoformat(), telegram_enabled=True,
            ollama_enabled=False, execution_mode='paper', entries_paused=daily_block,
            daily_loss_limit_reached=daily_block, daily_realized_pnl=str(risk.daily_realized_pnl),
            portfolio_id=portfolio['portfolio_id'], cash=portfolio['cash_balance'],
            total_realized_pnl=portfolio['realized_pnl'], open_positions=len(portfolio['positions']),
            accounting_reconciled=portfolio['accounting_reconciled'])
        Path('analysis/telegram_migration_recovery_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result))
    finally:
        await db.dispose()


asyncio.run(main())
