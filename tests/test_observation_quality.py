from datetime import UTC, datetime, timedelta
from decimal import Decimal

from memebot.storage.database.experiments import horizon_coverage
from memebot.storage.database.models import TradeOutcomeRecord
from memebot.storage.database.outcomes import update_post_exit


def test_post_exit_labels_preserve_realized_trade_and_reject_late_horizon() -> None:
    now = datetime(2026, 9, 13, tzinfo=UTC)
    outcome = TradeOutcomeRecord(
        exit_at=now,
        actual_exit_price_raw=Decimal(1),
        actual_entry_price_raw=Decimal(1),
        realized_pnl=Decimal(-1),
        mfe_percent=Decimal(5),
        mae_percent=Decimal(-12),
        post_exit_json=None,
    )
    update_post_exit(outcome, Decimal(2), now + timedelta(seconds=3601))
    assert outcome.realized_pnl == -1
    assert outcome.mfe_percent == 5
    assert outcome.mae_percent == -12
    state = outcome.post_exit_json
    assert state["horizons"]["3600"]["coverage"] == "observed"
    assert state["horizons"]["60"]["coverage"] == "gap"
    assert state["horizons"]["60"]["return_percent"] is None
    update_post_exit(outcome, Decimal(100), now + timedelta(seconds=3600))
    assert outcome.post_exit_json == state


def test_missing_coverage_is_not_counted_as_observed_or_zero_return() -> None:
    result = horizon_coverage(
        [
            {},
            {"60": {"coverage": "gap"}},
            {"60": {"coverage": "observed", "return_percent": "10"}},
            {"60": {"return_percent": "10"}},
        ]
    )
    assert result["60"] == {
        "observed": 1,
        "gap": 1,
        "missing_or_pending": 1,
        "legacy_unverified": 1,
    }
