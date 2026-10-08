"""Verify an additive price-mark migration without launching providers or trading."""

import asyncio
import json
import sys
from pathlib import Path

import asyncpg

from memebot.core.config import Settings
from memebot.storage.database.migrations import upgrade_database

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "analysis/price_database_validation.json"
TABLES = (
    "paper_positions", "paper_orders", "trade_outcomes", "paper_portfolios",
    "experiment_runs", "strategy_configurations",
)


async def snapshot():
    settings = Settings()
    connection = await asyncpg.connect(settings.database_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        async with connection.transaction(readonly=True, isolation="repeatable_read"):
            counts = {table: await connection.fetchval(f"SELECT count(*) FROM {table}") for table in TABLES}
            control = await connection.fetchrow(
                "SELECT entries_paused, active_strategy_key, base_position_percent, "
                "max_position_percent, max_open_positions, stop_loss_percent, "
                "take_profit_percent, trailing_stop_percent, max_holding_seconds "
                "FROM trading_control LIMIT 1"
            )
            return {
                "head": await connection.fetchval("SELECT version_num FROM alembic_version"),
                "counts": counts,
                "control": dict(control) if control else None,
                "runner_experiments": await connection.fetchval(
                    "SELECT count(*) FROM experiment_runs WHERE name='runner-edge-prospective-v1'"
                ),
                "open_positions": await connection.fetchval("SELECT count(*) FROM paper_positions WHERE status='open'"),
                "execution_mode": settings.execution_mode,
            }
    finally:
        await connection.close()


if sys.argv[1] == "before":
    result = {"before": asyncio.run(snapshot())}
    PATH.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
elif sys.argv[1] == "upgrade":
    result = json.loads(PATH.read_text(encoding="utf-8"))
    if result["before"]["head"] != "20260913_0015":
        raise ValueError("Refusing unrelated migrations; expected existing head 0015")
    upgrade_database(Settings().database_url)
    after = json.loads(json.dumps(asyncio.run(snapshot()), default=str))
    for key in ("counts", "control", "runner_experiments", "open_positions", "execution_mode"):
        if after[key] != result["before"][key]:
            raise ValueError(f"Unexpected change after additive migration: {key}")
    result.update(after=after, preserved_history_and_controls=True)
    PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
else:
    raise ValueError("expected before or upgrade")
print(json.dumps(result, indent=2, default=str))
