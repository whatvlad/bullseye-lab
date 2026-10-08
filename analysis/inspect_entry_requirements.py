"""Read the measured experiment configuration; export only non-secret entry controls."""
import asyncio, json
from pathlib import Path
from sqlalchemy import select
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import ExperimentRunRecord

async def main():
    run=json.loads(Path('analysis/paper_run_state.json').read_text(encoding='utf-8'))
    db=Database(create_database_engine(Settings().database_url))
    async with db.sessions() as session:
        exp=await session.scalar(select(ExperimentRunRecord).where(ExperimentRunRecord.name==run['experiment_name']))
        snap=exp.configuration_snapshot_json
    params=snap['settings']['execution_parameters']
    selected={k:v for k,v in params.items() if k.startswith(('risk_','paper_','alpha_','pulse_','ollama_')) and not k.endswith('_url')}
    result={'experiment':run['experiment_name'],'strategy':snap['strategy'],
            'trading_control':snap['trading_control'],'settings':selected,
            'pulse_presets':json.loads(Path(params['pulse_presets_file']).read_text(encoding='utf-8'))}
    Path('analysis/paper_entry_requirements.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print(json.dumps(result,indent=2,default=str))
    await db.dispose()
asyncio.run(main())
