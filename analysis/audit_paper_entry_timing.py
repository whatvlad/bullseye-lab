"""Read-only timing evidence for approved PAPER buys, without inferred LLM timing."""
import asyncio,json
from datetime import datetime,UTC
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from memebot.core.config import Settings
from memebot.storage.database.engine import Database,create_database_engine
from memebot.storage.database.models import PaperOrderRecord,StrategyDecisionRecord,DomainEventRecord,ExperimentRunRecord

def dt(value):
    return datetime.fromisoformat(value) if value else None

async def main():
    state=json.loads(Path('analysis/paper_run_state.json').read_text(encoding='utf-8'))
    db=Database(create_database_engine(Settings().database_url)); result=[]
    async with db.sessions() as session:
        exp=await session.scalar(select(ExperimentRunRecord).where(ExperimentRunRecord.name==state['experiment_name']))
        orders=list(await session.scalars(select(PaperOrderRecord).where(PaperOrderRecord.portfolio_id==exp.portfolio_id,PaperOrderRecord.side=='buy').order_by(PaperOrderRecord.created_at)))
        for o in orders:
            d=await session.get(StrategyDecisionRecord,o.decision_event_id)
            feature=await session.get(DomainEventRecord,d.feature_event_id) if d.feature_event_id else None
            risk=await session.get(DomainEventRecord,d.risk_event_id)
            event=await session.get(DomainEventRecord,o.event_id)
            f_at=feature.source_event_at if feature else None
            bank=(risk.payload.get('current_execution_state') or {}) if risk else {}
            price=event.payload.get('result',{}).get('price_evidence',{})
            row={'mint':o.mint,'status':o.status,'reason':o.rejection_reason,
                 'feature_at':f_at,'feature_received_at':feature.provider_received_at if feature else None,
                 'feature_ingested_at':feature.ingested_at if feature else None,
                 'risk_facts_at':risk.source_event_at if risk else None,
                 'pre_risk_bank_received_at':bank.get('received_timestamp'),
                 'decision_timestamp_before_model':d.decided_at,'order_recorded_at':o.created_at,
                 'execution_bank_received_at':price.get('received_timestamp'),
                 'signal_age_at_risk_seconds':(d.decided_at-f_at).total_seconds() if f_at else None,
                 'signal_age_at_order_seconds':(o.created_at-f_at).total_seconds() if f_at else None,
                 'decision_to_order_seconds':(o.created_at-d.decided_at).total_seconds(),
                 'feature_receipt_delay_seconds':(feature.ingested_at-f_at).total_seconds() if feature else None,
                 'signal_price_available':feature.payload.get('latest_price_raw') is not None if feature else False,
                 'slot':feature.source_slot if feature else None}
            result.append(row)
    report={'experiment':exp.name,'snapshot_at':datetime.now(UTC),
            'signal_max_age_seconds':exp.configuration_snapshot_json['settings']['execution_parameters']['paper_max_signal_age_seconds'],
            'notes':'decision timestamp is inherited from risk facts before Ollama. decision_to_order includes model, queue, and execution work; not an isolated inference duration.',
            'orders':result}
    Path('analysis/current_paper_entry_timing.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    print(json.dumps(report,indent=2,default=str)); await db.dispose()
asyncio.run(main())
