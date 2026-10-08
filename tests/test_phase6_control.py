from decimal import Decimal

import pytest

from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.registry import TokenRegistry
from memebot.strategies.presets import initial_strategy_presets

MINT = "So11111111111111111111111111111111111111112"


@pytest.mark.asyncio
async def test_runtime_controls_and_token_lists_are_persistent() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    controls = ControlRepository(database.sessions)
    await registry.ensure_strategy_configurations(initial_strategy_presets())

    initial = await controls.ensure(
        active_strategy_key="aggressive",
        base_position_percent=Decimal(5),
        max_position_percent=Decimal(10),
        max_open_positions=10,
        stop_loss_percent=Decimal(20),
        take_profit_percent=Decimal(50),
        trailing_stop_percent=Decimal(15),
        max_holding_seconds=1800,
    )
    assert initial.entries_paused is False
    assert (await controls.set_paused(True, user_id=123)).entries_paused is True
    automatically_paused, changed = await controls.pause_automatically()
    assert automatically_paused.entries_paused is True
    assert changed is False
    assert (
        await controls.set_active_strategy("balanced", user_id=123)
    ).active_strategy_key == "balanced"
    updated = await controls.update_risk(
        stop_loss_percent=Decimal(12), max_open_positions=4, user_id=123
    )
    assert updated.stop_loss_percent == Decimal(12)
    assert updated.max_open_positions == 4
    sized = await controls.update_sizing(
        base_position_percent=Decimal(3),
        max_position_percent=Decimal(7),
        user_id=123,
    )
    assert sized.base_position_percent == Decimal(3)
    assert sized.max_position_percent == Decimal(7)

    await controls.set_token_control(MINT, watchlisted=True, user_id=123)
    await controls.set_token_control(MINT, blacklisted=True, reason="operator", user_id=123)
    assert await controls.is_blacklisted(MINT) is True
    assert [item["mint"] for item in await controls.token_controls(kind="watchlist")] == [MINT]
    assert [item["mint"] for item in await controls.token_controls(kind="blacklist")] == [MINT]
    await database.dispose()


@pytest.mark.asyncio
async def test_control_validation_rejects_unsafe_values() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    controls = ControlRepository(database.sessions)
    await controls.ensure(
        active_strategy_key="aggressive",
        base_position_percent=Decimal(5),
        max_position_percent=Decimal(10),
        max_open_positions=10,
        stop_loss_percent=Decimal(20),
        take_profit_percent=Decimal(50),
        trailing_stop_percent=Decimal(15),
        max_holding_seconds=1800,
    )
    with pytest.raises(ValueError, match="base_position_exceeds_maximum"):
        await controls.update_sizing(
            base_position_percent=Decimal(11),
            max_position_percent=Decimal(10),
            user_id=1,
        )
    with pytest.raises(ValueError, match="max_open_positions_out_of_range"):
        await controls.update_risk(max_open_positions=0, user_id=1)
    with pytest.raises(ValueError, match="invalid_solana_mint"):
        await controls.set_token_control("A" * 32, watchlisted=True, user_id=1)
    await database.dispose()
