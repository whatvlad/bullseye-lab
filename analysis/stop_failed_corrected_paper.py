import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from sqlalchemy import func, select
from memebot.core.config import Settings
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.models import PaperPositionRecord

async def main():
    database = Database(create_database_engine(Settings().database_url))
    state_path = Path("analysis/paper_corrected_run_state.json")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    controls = ControlRepository(database.sessions)
    await controls.set_paused(True, user_id=0)
    async with database.sessions() as session:
        assert not await session.scalar(select(func.count()).select_from(PaperPositionRecord).where(PaperPositionRecord.status == "open"))
    experiments = ExperimentRepository(database.sessions)
    active = await experiments.active()
    assert active["name"] == state["experiment_name"]
    await experiments.stop()
    state.update(status="BLOCKED_PROVIDER_HTTP_429", ended_at=datetime.now(UTC).isoformat(),
                 candidates_observed=0, open_positions=0, closed_positions=0)
    Path("analysis/paper_corrected_failed_feed_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({"failed_feed_experiment_archived": active["name"], "open_positions": 0}))
    await database.dispose()

asyncio.run(main())
