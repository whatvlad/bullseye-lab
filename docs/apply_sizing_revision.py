"""Apply the user-requested sizing change without abandoning existing positions."""

import asyncio
import argparse
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.core.fingerprint import experiment_matches
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.models import ExperimentRunRecord, TradingControlRecord
from memebot.storage.database.registry import TokenRegistry


async def main(reason: str) -> None:
    settings = Settings()
    assert settings.execution_mode == "paper"
    db = Database(create_database_engine(settings.database_url))
    try:
        controls = ControlRepository(db.sessions)
        experiments = ExperimentRepository(db.sessions)
        active = await experiments.active()
        assert active is not None
        if experiment_matches(active, settings.safe_summary(), await controls.get()):
            print("Sizing configuration already applied")
            return
        positions = await TokenRegistry(db.sessions).open_positions()
        backup = Path("docs/sizing-revision-before.json")
        if not backup.exists():
            backup.write_text(json.dumps(active, indent=2, default=str), encoding="utf-8")
        async with db.sessions() as session, session.begin():
            control = await session.get(TradingControlRecord, 1, with_for_update=True)
            record = await session.scalar(
                select(ExperimentRunRecord)
                .where(ExperimentRunRecord.status == "active")
                .with_for_update()
            )
            assert control is not None and control.entries_paused and record is not None
            snapshot = dict(record.configuration_snapshot_json)
            history = list(snapshot.pop("configuration_history", []))
            changed_at = utc_now().isoformat()
            history.append(
                {
                    "replaced_at": changed_at,
                    "reason": reason,
                    "snapshot": snapshot,
                    "open_position_ids": [str(p.position_id) for p in positions],
                }
            )
            control.base_position_percent = Decimal(30)
            control.max_position_percent = Decimal(40)
            control.updated_by_telegram_user_id = None
            new_snapshot = dict(snapshot)
            new_snapshot["captured_at"] = changed_at
            new_snapshot["settings"] = settings.safe_summary()
            new_snapshot["trading_control"] = {
                **snapshot["trading_control"],
                "base_position_percent": "30.0000",
                "max_position_percent": "40.0000",
            }
            new_snapshot["configuration_history"] = history
            record.configuration_snapshot_json = new_snapshot
        active = await experiments.active()
        assert experiment_matches(active, settings.safe_summary(), await controls.get())
        Path("docs/sizing-revision-after.json").write_text(
            json.dumps(active, indent=2, default=str), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "name": active["name"],
                    "positions_preserved": len(positions),
                    "sizing": "10 minimum, up to 40 percent",
                    "status": "applied_paused",
                }
            )
        )
    finally:
        await db.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reason", default="Apply Pulse, adaptive sizing and migration recovery; preserve open positions")
    asyncio.run(main(parser.parse_args().reason))
