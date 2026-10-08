"""Prepare the approved paper baseline; preserve old portfolios, refuse open positions."""

import asyncio
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from memebot.core.config import Settings
from memebot.core.fingerprint import experiment_matches
from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.registry import TokenRegistry
from memebot.strategies.presets import initial_strategy_presets

NAME = "sniper-v9-forward-2026-09-13"


async def main() -> None:
    settings = Settings()
    assert settings.execution_mode == "paper"
    db = Database(create_database_engine(settings.database_url))
    registry = TokenRegistry(db.sessions)
    controls = ControlRepository(db.sessions)
    experiments = ExperimentRepository(db.sessions)
    try:
        active = await experiments.active()
        if active and active["name"] == NAME:
            assert experiment_matches(active, settings.safe_summary(), await controls.get())
            print(json.dumps({"name": NAME, "status": "already_prepared"}))
            return
        if await registry.open_positions():
            raise RuntimeError(
                "Existing open positions: preserving them; no experiment replacement"
            )
        before = {"experiment": active, "controls": asdict(await controls.get())}
        before_path = Path("docs/sniper-preparation-before.json")
        if not before_path.exists():
            before_path.write_text(json.dumps(before, indent=2, default=str), encoding="utf-8")
        await controls.pause_automatically()
        if active:
            await experiments.stop()
        await registry.ensure_strategy_configurations(initial_strategy_presets())
        await controls.set_active_strategy("balanced", user_id=0)
        await controls.update_risk(
            stop_loss_percent=Decimal(12),
            take_profit_percent=Decimal(100),
            trailing_stop_percent=Decimal(18),
            max_open_positions=5,
            user_id=0,
        )
        await controls.update_sizing(
            base_position_percent=Decimal(8), max_position_percent=Decimal(8), user_id=0
        )
        result = await experiments.start(
            name=NAME,
            initial_cash=Decimal(100),
            currency="USDT",
            settings_snapshot=settings.safe_summary(),
            notes="v9 corrected execution and real reserve marks; early demand baseline. Separate post-graduation shadow preset. No profitability claim; paper only.",
        )
        assert experiment_matches(result, settings.safe_summary(), await controls.get())
        Path("docs/sniper-experiment.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )
        print(
            json.dumps(
                {"name": NAME, "portfolio_id": result["portfolio_id"], "status": "prepared_paused"}
            )
        )
    finally:
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
