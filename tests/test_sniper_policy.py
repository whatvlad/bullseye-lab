from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from memebot.core.config import Settings
from memebot.core.fingerprint import experiment_matches
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.paper.exits import exit_intent
from memebot.paper.models import PositionSnapshot
from memebot.storage.database.control import TradingControlSnapshot

NOW = datetime(2026, 9, 13, tzinfo=UTC)
CONTROL = TradingControlSnapshot(
    False, "balanced", Decimal(8), Decimal(8), 5, Decimal(12), Decimal(100), Decimal(18), 1800
)
POSITION = PositionSnapshot(
    UUID(int=1),
    UUID(int=2),
    "mint",
    "balanced",
    "market",
    LaunchVenue.PUMP_FUN,
    MarketLifecycle.BONDING_CURVE,
    Decimal(1000),
    Decimal(10),
    Decimal(0),
    Decimal(1),
    Decimal(1),
    NOW,
    False,
)
SETTINGS = Settings(_env_file=None)


def test_no_exit_before_actual_entry() -> None:
    assert (
        exit_intent(
            POSITION,
            Decimal("0.1"),
            NOW - timedelta(milliseconds=1),
            CONTROL,
            SETTINGS,
            hazard=True,
        )
        is None
    )


def test_stop_is_cancelled_if_execution_price_recovers() -> None:
    assert exit_intent(POSITION, Decimal("0.85"), NOW, CONTROL, SETTINGS).reason == "stop_loss"
    assert exit_intent(POSITION, Decimal("0.95"), NOW, CONTROL, SETTINGS) is None


def test_runner_survives_normal_pullback_and_exits_large_drawdown() -> None:
    runner = replace(POSITION, peak_price_raw=Decimal(3), partial_take_profit_taken=True)
    assert (
        exit_intent(runner, Decimal("2.5"), NOW + timedelta(minutes=40), CONTROL, SETTINGS) is None
    )
    assert (
        exit_intent(runner, Decimal(2), NOW + timedelta(minutes=40), CONTROL, SETTINGS).reason
        == "trailing_stop"
    )


def test_hazard_cannot_sell_profitable_position() -> None:
    assert exit_intent(POSITION, Decimal("1.05"), NOW, CONTROL, SETTINGS, hazard=True) is None


def test_experiment_fingerprint_detects_code_settings_and_control_drift() -> None:
    summary = {"code_fingerprint": "abc", "execution_parameters": {"latency": 800}}
    control = {k: str(v) for k, v in asdict(CONTROL).items() if k != "entries_paused"}
    experiment = {"configuration_snapshot": {"settings": summary, "trading_control": control}}
    assert experiment_matches(experiment, summary, CONTROL)
    assert experiment_matches(experiment, summary, replace(CONTROL, entries_paused=True))
    assert not experiment_matches(experiment, {**summary, "code_fingerprint": "def"}, CONTROL)
    assert not experiment_matches(
        experiment, {**summary, "execution_parameters": {"latency": 0}}, CONTROL
    )
    assert not experiment_matches(
        experiment, summary, replace(CONTROL, stop_loss_percent=Decimal(30))
    )
