"""Bounded live-data smoke test; keep entries paused and suppress notifications."""

import asyncio

import memebot.apps.worker as worker
from memebot.core.config import Settings
from memebot.core.fingerprint import experiment_matches
from memebot.core.logging import configure_logging
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository


async def main() -> None:
    settings = Settings()
    assert settings.execution_mode == "paper"
    db = Database(create_database_engine(settings.database_url))
    try:
        control = await ControlRepository(db.sessions).get()
        assert control is not None and control.entries_paused
        assert experiment_matches(await ExperimentRepository(db.sessions).active(), settings.safe_summary(), control)
    finally:
        await db.dispose()
    worker._telegram_notifier = lambda settings: None
    configure_logging(settings.log_level, settings.log_format)
    await worker.run_discovery_worker(settings, run_seconds=60)


if __name__ == "__main__":
    asyncio.run(main())
