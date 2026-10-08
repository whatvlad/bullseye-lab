import asyncio,json
from datetime import datetime,UTC
from pathlib import Path
from sqlalchemy import select
from memebot.core.config import Settings
from memebot.storage.database.engine import Database,create_database_engine
from memebot.storage.database.models import DomainEventRecord,ExperimentRunRecord
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID

def stats(values):
    values=sorted(values)
    def pct(p):return values[min(len(values)-1,int((len(values)-1)*p))] if values else None
    return {'n':len(values),'p50_seconds':pct(.5),'p90_seconds':pct(.9),'p95_seconds':pct(.95),
            'max_seconds':max(values) if values else None,
            'over_5s':sum(v>5 for v in values),'over_10s':sum(v>10 for v in values),'over_25s':sum(v>25 for v in values)}

async def main():
    run=json.loads(Path('analysis/paper_run_state.json').read_text(encoding='utf-8'))
    audit=json.loads(Path('analysis/current_paper_funnel_audit.json').read_text(encoding='utf-8'))
    end=datetime.fromisoformat(audit['snapshot_end'])
    db=Database(create_database_engine(Settings().database_url)); all_delays=[]; standard=[]; estimated=0
    async with db.sessions() as session:
        exp=await session.scalar(select(ExperimentRunRecord).where(ExperimentRunRecord.name==run['experiment_name']))
        rows=await session.execute(select(DomainEventRecord.source_event_at,DomainEventRecord.provider_received_at,
            DomainEventRecord.payload['normalized_state']['program'].as_string(),
            DomainEventRecord.payload['normalized_state']['is_mayhem_mode'].as_boolean(),
            DomainEventRecord.payload['source_timestamp_estimated'].as_boolean()).where(
                DomainEventRecord.provider=='solana_rpc_pump',DomainEventRecord.event_type=='token.trade',
                DomainEventRecord.ingested_at>=exp.started_at,DomainEventRecord.ingested_at<=end))
        for source,received,program,mayhem,is_estimated in rows:
            if is_estimated: estimated+=1; continue
            if received is None:continue
            delay=(received-source).total_seconds(); all_delays.append(delay)
            if program==PUMP_PROGRAM_ID and mayhem is False:standard.append(delay)
    result={'snapshot_end':end,'all_native_trades':stats(all_delays),'standard_non_mayhem_pump_trades':stats(standard),
            'estimated_timestamps_excluded':estimated,'basis':'provider local processing receipt minus program event timestamp; does not isolate upstream delivery from local receive backlog'}
    Path('analysis/current_paper_feed_delay.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print(json.dumps(result,indent=2,default=str));await db.dispose()
asyncio.run(main())
