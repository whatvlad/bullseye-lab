import asyncio, json
from collections import Counter
from sqlalchemy import select
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import DomainEventRecord
from memebot.eligibility import research_rejection, paper_candidate_rejection

async def main():
    state=json.load(open('analysis/paper_run_state.json',encoding='utf-8'))
    from datetime import datetime
    db=Database(create_database_engine(Settings().database_url))
    async with db.sessions() as session:
        rows=list(await session.scalars(select(DomainEventRecord).where(
            DomainEventRecord.ingested_at>=datetime.fromisoformat(state['observation_started_at']),
            DomainEventRecord.event_type=='token.trade')))
    counts=Counter(); samples=[]
    for row in rows:
        raw=row.payload.get('normalized_state',{})
        from memebot.market_state import NormalizedMarketState
        normalized=NormalizedMarketState(**raw)
        e=normalized.evidence()
        old,new=research_rejection(e),paper_candidate_rejection(e)
        counts[(old,new)]+=1
        if len(samples)<5: samples.append({k:e.get(k) for k in ['state_reason','state_quality','state_semantics','continuity_status','program','is_mayhem_mode','invalidation_reason']})
    print(json.dumps({'counts':[{'old':k[0],'current_candidate':k[1],'n':v} for k,v in counts.items()], 'samples':samples},default=str))
    await db.dispose()
asyncio.run(main())
