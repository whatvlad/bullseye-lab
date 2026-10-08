"""Bounded read-only snapshot of the active PAPER portfolio's actual fills."""
import asyncio
import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from sqlalchemy import inspect, select, text
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import (
    ExperimentRunRecord, PaperPortfolioRecord, PaperPositionRecord, PaperOrderRecord,
    TradeOutcomeRecord, TokenRecord, DomainEventRecord,
    TradingControlRecord, ProviderHealthRecord,
)

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='analysis/loss_audit_20261003')
parser.add_argument('--active-portfolio', action='store_true')
args = parser.parse_args()
ROOT = Path(args.output)
ROOT.mkdir(parents=True, exist_ok=True)

def row(record):
    return {column.key: getattr(record, column.key) for column in inspect(type(record)).columns}

def write(name, data):
    (ROOT/name).write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')

async def main():
    settings = Settings(pumpportal_api_key=None)
    database = Database(create_database_engine(settings.database_url))
    try:
        async with database.sessions() as session, session.begin():
            await session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            run = await session.scalar(select(ExperimentRunRecord).where(ExperimentRunRecord.status == 'active'))
            assert run is not None
            pid = run.portfolio_id
            controls = await session.get(TradingControlRecord, 1)
            health = list(await session.scalars(select(ProviderHealthRecord)))
            portfolio_headers = list(await session.scalars(select(PaperPortfolioRecord).order_by(PaperPortfolioRecord.created_at)))
            run_headers = list(await session.scalars(select(ExperimentRunRecord).order_by(ExperimentRunRecord.created_at)))
            portfolio = await session.get(PaperPortfolioRecord, pid)
            if args.active_portfolio:
                portfolio = await session.scalar(select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True)))
                assert portfolio is not None
                pid = portfolio.id
            positions = list(await session.scalars(select(PaperPositionRecord).where(PaperPositionRecord.portfolio_id == pid).order_by(PaperPositionRecord.opened_at)))
            fills = list(await session.scalars(select(PaperOrderRecord).where(PaperOrderRecord.portfolio_id == pid, PaperOrderRecord.status == 'filled').order_by(PaperOrderRecord.filled_at)))
            outcomes = list(await session.scalars(select(TradeOutcomeRecord).where(TradeOutcomeRecord.portfolio_id == pid).order_by(TradeOutcomeRecord.entry_at)))
            tokens = list(await session.scalars(select(TokenRecord).where(TokenRecord.id.in_([p.token_id for p in positions]))))
            evidence_ids = {o.event_id for o in fills} | {o.decision_event_id for o in fills if o.decision_event_id} | {t.entry_decision_event_id for t in outcomes if t.entry_decision_event_id}
            evidence = list(await session.scalars(select(DomainEventRecord).where(DomainEventRecord.event_id.in_(evidence_ids))))
            extra_ids = set()
            from uuid import UUID
            for event in evidence:
                for key in ('risk_event_id', 'feature_event_id', 'trigger_event_id'):
                    value = event.payload.get(key)
                    if value:
                        try: extra_ids.add(UUID(value))
                        except (ValueError, TypeError): pass
            extras = list(await session.scalars(select(DomainEventRecord).where(DomainEventRecord.event_id.in_(extra_ids))))
            rejects = list(await session.scalars(select(PaperOrderRecord).where(PaperOrderRecord.portfolio_id == pid, PaperOrderRecord.side == 'sell', PaperOrderRecord.status != 'filled').order_by(PaperOrderRecord.created_at)))
        write('snapshot.json', {'captured_at': datetime.now(UTC), 'run': row(run), 'portfolio': row(portfolio),
            'trading_control': row(controls) if controls else None,
            'provider_health': [row(p) for p in health],
            'portfolio_headers': [row(p) for p in portfolio_headers],
            'run_headers': [{k:v for k,v in row(r).items() if k != 'configuration_snapshot_json'} for r in run_headers],
            'positions': [row(p) for p in positions], 'filled_orders': [row(o) for o in fills],
            'outcomes': [row(t) for t in outcomes], 'tokens': [row(t) for t in tokens],
            'evidence': [row(e) for e in evidence + extras], 'exit_rejections': [row(o) for o in rejects]})
        summary = settings.safe_summary()
        summary.pop('database_url', None)
        write('current_settings.json', summary)
        print(json.dumps({'experiment': run.name, 'portfolio_id': str(pid), 'positions': len(positions), 'fills': len(fills), 'outcomes': len(outcomes),
            'realized_pnl': str(portfolio.realized_pnl), 'cash': str(portfolio.cash_balance),
            'exit_rejections': len(rejects), 'exit_reasons': dict(Counter(o.exit_reason for o in fills if o.side == 'sell')),
            'rejected_exit_reasons': dict(Counter(o.rejection_reason for o in rejects))}))
    finally:
        await database.dispose()

asyncio.run(main())
