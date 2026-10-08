"""Activate the reviewed paper sniper revision without replacing the portfolio."""

import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import select

from memebot.core.config import Settings
from memebot.core.fingerprint import experiment_matches
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.models import ExperimentRunRecord, TradingControlRecord
from memebot.storage.database.registry import TokenRegistry
from memebot.strategies.presets import initial_strategy_presets


async def main() -> None:
    settings = Settings()
    if settings.execution_mode != "paper":
        raise RuntimeError("This revision applies to paper trading only")
    db = Database(create_database_engine(settings.database_url))
    try:
        registry = TokenRegistry(db.sessions)
        controls = ControlRepository(db.sessions)
        experiments = ExperimentRepository(db.sessions)
        presets = initial_strategy_presets()
        aggressive = next(item for item in presets if item.key == "aggressive")
        await registry.ensure_strategy_configurations(presets)
        before = await experiments.active()
        if before is None:
            raise RuntimeError("No active paper experiment to revise")
        positions = await registry.open_positions()
        if before["strategy_version_id"] == str(aggressive.version_id) and experiment_matches(
            before, settings.safe_summary(), await controls.get()
        ):
            print("Paper sniper revision already active")
            return
        async with db.sessions() as session, session.begin():
            control = await session.get(TradingControlRecord, 1, with_for_update=True)
            record = await session.scalar(
                select(ExperimentRunRecord)
                .where(ExperimentRunRecord.status == "active")
                .with_for_update()
            )
            if control is None or record is None:
                raise RuntimeError("Trading control or active experiment disappeared")
            was_paused = control.entries_paused
            control.entries_paused = True
            snapshot = dict(record.configuration_snapshot_json)
            history = list(snapshot.pop("configuration_history", []))
            changed_at = datetime.now(UTC).isoformat()
            history.append(
                {
                    "replaced_at": changed_at,
                    "reason": "Aggressive v10 paper sniper; 5k cap and 12s signal TTL",
                    "snapshot": snapshot,
                    "open_position_ids": [str(position.position_id) for position in positions],
                }
            )
            control.active_strategy_key = aggressive.key
            control.updated_by_telegram_user_id = None
            record.strategy_key = aggressive.key
            record.strategy_version_id = aggressive.version_id
            record.configuration_snapshot_json = {
                **snapshot,
                "captured_at": changed_at,
                "settings": settings.safe_summary(),
                "trading_control": {
                    **snapshot["trading_control"],
                    "active_strategy_key": aggressive.key,
                },
                "configuration_history": history,
            }
            control.entries_paused = was_paused
        after = await experiments.active()
        if not experiment_matches(after, settings.safe_summary(), await controls.get()):
            raise RuntimeError("Revised experiment fingerprint does not match runtime")
        print(
            json.dumps(
                {
                    "active_strategy": aggressive.key,
                    "version": aggressive.version,
                    "open_positions_preserved": len(positions),
                    "entries_paused": (await controls.get()).entries_paused,
                    "experiment": after["name"],
                }
            )
        )
    finally:
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
