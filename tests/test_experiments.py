from decimal import Decimal

import pytest

from memebot.storage.database.control import ControlRepository
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.registry import TokenRegistry
from memebot.strategies.presets import initial_strategy_presets


@pytest.mark.asyncio
async def test_clean_experiment_captures_config_and_uses_isolated_portfolio() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    controls = ControlRepository(database.sessions)
    experiments = ExperimentRepository(database.sessions)
    configurations = initial_strategy_presets()
    await registry.ensure_strategy_configurations(configurations)
    balanced = next(item for item in configurations if item.key == "balanced")
    await controls.ensure(
        active_strategy_key=balanced.key,
        base_position_percent=Decimal(3),
        max_position_percent=Decimal(20),
        max_open_positions=5,
        stop_loss_percent=Decimal(20),
        take_profit_percent=Decimal(25),
        trailing_stop_percent=Decimal(8),
        max_holding_seconds=1800,
    )
    await controls.set_paused(True, user_id=0)

    started = await experiments.start(
        name="baseline-v1",
        initial_cash=Decimal(100),
        currency="USDT",
        settings_snapshot={"execution_mode": "paper"},
    )

    assert started["status"] == "active"
    assert started["strategy_key"] == "balanced"
    assert Decimal(
        started["configuration_snapshot"]["trading_control"]["base_position_percent"]
    ) == Decimal(3)
    assert started["configuration_snapshot"]["strategy"]["active_for_execution"] is True
    assert started["configuration_snapshot"]["strategy"]["activation_source"] == "trading_control"
    portfolio = await registry.active_paper_portfolio()
    assert portfolio is not None
    assert str(portfolio.portfolio_id) == started["portfolio_id"]
    report = await experiments.report("baseline-v1")
    assert report["sample"]["closed_trades"] == 0
    assert report["performance"]["realized_pnl"] == "0"
    assert report["segments"]["closed_trades_by_score"] == {}
    assert report["segments"]["closed_trades_by_position_size"] == {}
    assert report["segments"]["decision_actions"] == {}
    assert report["segments"]["decision_reasons"] == {}
    assert report["segments"]["decision_reason_details"] == {}
    assert report["segments"]["recent_active_decisions"] == []
    assert report["segments"]["risk_critical_unknowns"] == {}
    assert report["segments"]["risk_unknown_details"] == {}

    stopped = await experiments.stop()
    assert stopped["status"] == "stopped"
    assert (await experiments.active()) is None
    await database.dispose()


@pytest.mark.asyncio
async def test_experiment_requires_paused_entries() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    controls = ControlRepository(database.sessions)
    experiments = ExperimentRepository(database.sessions)
    configurations = initial_strategy_presets()
    await registry.ensure_strategy_configurations(configurations)
    balanced = next(item for item in configurations if item.key == "balanced")
    await controls.ensure(
        active_strategy_key=balanced.key,
        base_position_percent=Decimal(3),
        max_position_percent=Decimal(20),
        max_open_positions=5,
        stop_loss_percent=Decimal(20),
        take_profit_percent=Decimal(25),
        trailing_stop_percent=Decimal(8),
        max_holding_seconds=1800,
    )

    with pytest.raises(ValueError, match="pause entries"):
        await experiments.start(
            name="unsafe-start",
            initial_cash=Decimal(100),
            currency="USDT",
            settings_snapshot={},
        )
    await database.dispose()
