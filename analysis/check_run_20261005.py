"""Read-only run and pasted-log health audit; no trading or provider calls."""
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, text

from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import (
    DomainEventRecord, PaperOrderRecord, PaperPositionRecord,
    StrategyDecisionRecord, TradingControlRecord,
)

ROOT = Path(__file__).resolve().parent
ATTACHMENT = Path('C:/Users/shiro/.codex/attachments/2f3c3be3-4652-4b49-93f4-ba71bd58e794/Вставленный текст.txt')


async def main():
    state = json.loads((ROOT / 'paper_run_state.json').read_text())
    start = datetime.fromisoformat(state['observation_started_at'])
    end = datetime.fromisoformat(state['ended_at'])
    pid = UUID(state['portfolio_id'])
    db = Database(create_database_engine(Settings().database_url))
    try:
        async with db.sessions() as s, s.begin():
            await s.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            event_counts = dict((await s.execute(select(DomainEventRecord.event_type, func.count()).where(
                DomainEventRecord.provider == 'solana_rpc_pump',
                DomainEventRecord.ingested_at.between(start, end)).group_by(DomainEventRecord.event_type))).all())
            decisions = list(await s.scalars(select(StrategyDecisionRecord).where(
                StrategyDecisionRecord.active_strategy.is_(True),
                StrategyDecisionRecord.decided_at.between(start, end))))
            ids = [d.event_id for d in decisions]
            raw = list(await s.scalars(select(DomainEventRecord).where(DomainEventRecord.event_id.in_(ids))))
            health = list(await s.scalars(select(DomainEventRecord).where(
                DomainEventRecord.event_type == 'provider.health_updated',
                DomainEventRecord.ingested_at.between(start, end))))
            orders = list(await s.scalars(select(PaperOrderRecord).where(PaperOrderRecord.portfolio_id == pid)))
            positions = list(await s.scalars(select(PaperPositionRecord).where(PaperPositionRecord.portfolio_id == pid)))
            all_open = await s.scalar(select(func.count()).select_from(PaperPositionRecord).where(PaperPositionRecord.status == 'open'))
            latest = await s.scalar(select(func.max(DomainEventRecord.ingested_at)).where(DomainEventRecord.provider == 'solana_rpc_pump'))
            control = await s.get(TradingControlRecord, 1)
        rows = []
        for line in ATTACHMENT.read_text(encoding='utf-8-sig').splitlines():
            try:
                r = json.loads(line)
                if isinstance(r, dict):
                    rows.append(r)
            except ValueError:
                pass
        progress = [r for r in rows if r.get('event') == 'websocket_receive_progress']
        runtime = [r for r in rows if r.get('event') == 'runtime_metrics']
        reasons = Counter(r for d in decisions for r in d.reasons)
        evidence = [r.payload.get('price_evidence') or {} for r in raw]
        result = {
            'checked_at_utc': datetime.now(UTC), 'run': state,
            'entries_paused': control.entries_paused if control else None,
            'latest_native_event': latest, 'events': event_counts,
            'decisions': len(decisions), 'candidate_tokens': len({d.token_id for d in decisions}),
            'actions': dict(Counter(d.action for d in decisions)),
            'reasons': dict(reasons.most_common()),
            'price_state_reasons': dict(Counter(e.get('invalidation_reason') or e.get('state_reason') or 'NO_STATE_REASON' for e in evidence)),
            'orders': len(orders), 'order_status': dict(Counter(o.status for o in orders)),
            'positions': len(positions), 'all_open_positions': all_open,
            'health_counts': dict(Counter(r.payload.get('error_code') for r in health if r.payload.get('state') == 'degraded')),
            'health_timeline': [{'at': r.ingested_at, 'state': r.payload.get('state'), 'error': r.payload.get('error_code')} for r in health],
            'pasted_log': {
                'parsed_rows': len(rows), 'first_at': rows[0].get('timestamp') if rows else None,
                'last_at': rows[-1].get('timestamp') if rows else None,
                'event_counts': dict(Counter(r.get('event') for r in rows)),
                'max_sampled_queue_lag_ms': max((r.get('queue_lag_ms', 0) for r in progress), default=0),
                'max_sampled_queue_depth': max((r.get('queue_depth', 0) for r in progress), default=0),
                'disconnects': [r for r in rows if r.get('event') == 'websocket_disconnect'],
                'full_stream': [r for r in rows if r.get('event') in {'executed_evidence_stopped', 'executed_evidence_unavailable', 'executed_processor_failed'}],
                'latest_executed_metrics': runtime[-1].get('executed_evidence') if runtime else None,
                'latest_rpc_requests': runtime[-1].get('primary_rpc', {}).get('requests_by_method') if runtime else None,
            },
        }
        (ROOT / 'health_audit_20261005.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
        print(json.dumps(result, indent=2, default=str))
    finally:
        await db.dispose()


asyncio.run(main())
