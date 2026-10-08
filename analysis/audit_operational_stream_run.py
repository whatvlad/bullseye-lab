"""Read-only diagnosis of the last operational PAPER observation window."""
import asyncio
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, text
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import (
    DecisionOutcomeRecord, DomainEventRecord, PaperOrderRecord,
    PaperPositionRecord, TradingControlRecord,
)

ROOT = Path(__file__).resolve().parents[1]

async def main():
    state = json.loads((ROOT / 'analysis/paper_run_state.json').read_text())
    start = datetime.fromisoformat(state['observation_started_at'])
    end = datetime.fromisoformat(state['ended_at'])
    database = Database(create_database_engine(Settings().database_url))
    try:
        async with database.sessions() as session, session.begin():
            await session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            decisions = list(await session.scalars(select(DecisionOutcomeRecord).where(
                DecisionOutcomeRecord.active_strategy.is_(True),
                DecisionOutcomeRecord.decided_at >= start, DecisionOutcomeRecord.decided_at <= end)))
            events = dict((await session.execute(select(DomainEventRecord.event_type, func.count()).where(
                DomainEventRecord.provider == 'solana_rpc_pump',
                DomainEventRecord.ingested_at >= start, DomainEventRecord.ingested_at <= end
            ).group_by(DomainEventRecord.event_type))).all())
            health = list(await session.scalars(select(DomainEventRecord).where(
                DomainEventRecord.event_type == 'provider.health_updated',
                DomainEventRecord.ingested_at >= start, DomainEventRecord.ingested_at <= end)))
            pid = UUID(state['portfolio_id'])
            positions = await session.scalar(select(func.count()).select_from(PaperPositionRecord).where(PaperPositionRecord.portfolio_id == pid))
            orders = list(await session.scalars(select(PaperOrderRecord).where(PaperOrderRecord.portfolio_id == pid)))
            control = await session.get(TradingControlRecord, 1)
            ids = [d.decision_event_id for d in decisions]
            raw = {r.event_id: r.payload for r in await session.scalars(select(DomainEventRecord).where(DomainEventRecord.event_id.in_(ids)))} if ids else {}
        reasons, state_reasons = Counter(), Counter()
        for decision in decisions:
            reasons.update(decision.decision_reasons)
            evidence = raw.get(decision.decision_event_id, {}).get('price_evidence') or {}
            state_reasons[evidence.get('invalidation_reason') or evidence.get('state_reason') or 'NO_STATE_REASON'] += 1
        result = {'window': state, 'events': events, 'positions': positions,
                  'orders': len(orders), 'order_statuses': dict(Counter(o.status for o in orders)),
                  'decisions': len(decisions), 'unique_candidates': len({d.mint for d in decisions}),
                  'actions': dict(Counter(d.action for d in decisions)),
                  'execution_statuses': dict(Counter(d.execution_status for d in decisions)),
                  'decision_reasons': dict(reasons.most_common()), 'price_state_reasons': dict(state_reasons),
                  'entries_paused_now': control.entries_paused if control else None,
                  'health': [{'at': h.ingested_at, 'state': h.payload.get('state'),
                              'error_code': h.payload.get('error_code')} for h in health],
                  'sample_feature': decisions[0].feature_snapshot_json if decisions else None}
        (ROOT / 'analysis/operational_stream_run_audit.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
        result.pop('sample_feature')
        print(json.dumps(result, indent=2, default=str))
    finally:
        await database.dispose()

asyncio.run(main())
