"""Read-only consistent audit of the operational PAPER run currently selected."""
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, text

from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import (
    DomainEventRecord, PaperOrderRecord, StrategyDecisionRecord, TradingControlRecord,
    ExperimentRunRecord,
)


async def main():
    run = json.loads(Path('analysis/paper_run_state.json').read_text())
    start = datetime.fromisoformat(run['observation_started_at'])
    end = datetime.now(UTC)
    db = Database(create_database_engine(Settings().database_url))
    try:
        async with db.sessions() as s, s.begin():
            await s.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            control = await s.get(TradingControlRecord, 1)
            experiment = await s.scalar(select(ExperimentRunRecord).where(
                ExperimentRunRecord.portfolio_id == UUID(run['portfolio_id'])))
            counts = dict((await s.execute(select(DomainEventRecord.event_type, func.count()).where(
                DomainEventRecord.ingested_at.between(start, end)
            ).group_by(DomainEventRecord.event_type))).all())
            decisions = list(await s.scalars(select(StrategyDecisionRecord).where(
                StrategyDecisionRecord.active_strategy.is_(True),
                StrategyDecisionRecord.decided_at.between(start, end))))
            evidence = list(await s.scalars(select(DomainEventRecord.payload).join(
                StrategyDecisionRecord, StrategyDecisionRecord.event_id == DomainEventRecord.event_id
            ).where(StrategyDecisionRecord.active_strategy.is_(True),
                    StrategyDecisionRecord.decided_at.between(start, end))))
            orders = list(await s.scalars(select(PaperOrderRecord).where(
                PaperOrderRecord.portfolio_id == UUID(run['portfolio_id']))))
            health = list(await s.scalars(select(DomainEventRecord).where(
                DomainEventRecord.event_type == 'provider.health_updated',
                DomainEventRecord.ingested_at.between(start, end))))
            latest = await s.scalar(select(func.max(DomainEventRecord.ingested_at)).where(
                DomainEventRecord.provider == 'solana_rpc_pump'))
            trade_states = (await s.execute(text('''
                SELECT payload->'normalized_state'->>'continuity_status' AS state,
                       COALESCE(payload->'normalized_state'->>'invalidation_reason',
                                payload->'normalized_state'->>'reason') AS reason, count(*) AS n
                FROM domain_events WHERE provider='solana_rpc_pump' AND event_type='token.trade'
                AND ingested_at BETWEEN :start AND :end GROUP BY 1,2 ORDER BY 3 DESC
            '''), {'start':start, 'end':end})).mappings().all()
        prices = [e.get('price_evidence') or {} for e in evidence]
        recent = [d for d in decisions if d.decided_at >= end-timedelta(minutes=10)]
        report = {
            'run':run, 'checked_at':end, 'duration_minutes':(end-start).total_seconds()/60,
            'entries_paused':control.entries_paused if control else None,
            'experiment_status':experiment.status if experiment else None,
            'latest_native_event':latest, 'events':counts, 'active_decisions':len(decisions),
            'candidate_mints':len({d.token_id for d in decisions}),
            'actions':dict(Counter(d.action for d in decisions)),
            'reasons':dict(Counter(r for d in decisions for r in d.reasons).most_common()),
            'price_reasons':dict(Counter(p.get('invalidation_reason') or p.get('state_reason') or 'UNSPECIFIED' for p in prices)),
            'trade_states':[dict(r) for r in trade_states],
            'last_10min_decisions':len(recent),
            'last_10min_reasons':dict(Counter(r for d in recent for r in d.reasons).most_common()),
            'orders':len(orders), 'order_status':dict(Counter(o.status for o in orders)),
            'order_rejections':dict(Counter(o.rejection_reason for o in orders)),
            'health_counts':dict(Counter(r.payload.get('error_code') for r in health if r.payload.get('state')=='degraded')),
            'health_last':[{'at':r.ingested_at, 'state':r.payload.get('state'), 'error':r.payload.get('error_code')} for r in sorted(health,key=lambda r:r.ingested_at)[-8:]],
        }
        Path('analysis/current_no_trades_audit.json').write_text(json.dumps(report,indent=2,default=str))
        print(json.dumps(report,indent=2,default=str))
    finally:
        await db.dispose()


asyncio.run(main())
