from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from memebot.events.models import MarketFeatureSnapshotCreated, TokenTrade, TradeSide
from memebot.intelligence.features.models import RollingWindowMetrics
from memebot.models.market import MarketLifecycle, MarketValidationState
from memebot.paper.dump_hazard import has_dump_hazard

MINT = "So11111111111111111111111111111111111111112"
NOW = datetime(2026, 8, 23, tzinfo=UTC)


def _trade(side: TradeSide) -> TokenTrade:
    return TokenTrade(
        event_id=UUID(int=700),
        provider="test",
        source_event_at=NOW,
        mint=MINT,
        signature="7" * 32,
        side=side,
        token_amount=Decimal(10),
        quote_amount=Decimal(5),
        quote_asset="SOL",
    )


def _feature() -> MarketFeatureSnapshotCreated:
    metric = RollingWindowMetrics(
        window_seconds=30,
        trade_count=10,
        buy_count=3,
        sell_count=7,
        unique_buyers=3,
        unique_sellers=5,
        buy_volume_quote_raw=Decimal(200),
        sell_volume_quote_raw=Decimal(800),
        total_volume_quote_raw=Decimal(1000),
        flow_imbalance=Decimal("-0.6"),
        price_change_percent=Decimal(-15),
        volume_velocity_quote_raw_per_second=Decimal(10),
        transaction_rate_per_second=Decimal(1),
        latest_price_return_percent=Decimal(-9),
        latest_sell_size_mad_score=Decimal(7),
        quote_reserve_velocity_raw_per_second=Decimal(-10),
    )
    return MarketFeatureSnapshotCreated(
        event_id=UUID(int=701),
        provider="rolling_feature_engine",
        source_event_at=NOW,
        mint=MINT,
        trigger_event_id=UUID(int=700),
        lifecycle=MarketLifecycle.BONDING_CURVE,
        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        windows=(metric,),
    )


def test_dump_hazard_requires_sell_outlier_and_confirming_pressure() -> None:
    assert has_dump_hazard(_trade(TradeSide.SELL), _feature()) is True
    assert has_dump_hazard(_trade(TradeSide.BUY), _feature()) is False
    calm = _feature().model_copy(
        update={
            "windows": (
                _feature()
                .windows[0]
                .model_copy(
                    update={
                        "latest_price_return_percent": Decimal(-1),
                        "latest_sell_size_mad_score": Decimal(1),
                    }
                ),
            )
        }
    )
    assert has_dump_hazard(_trade(TradeSide.SELL), calm) is False


def test_tiny_sell_outlier_does_not_trigger_hazard() -> None:
    metric = (
        _feature()
        .windows[0]
        .model_copy(
            update={
                "latest_price_return_percent": Decimal("-0.01"),
                "latest_sell_size_mad_score": Decimal(999),
                "latest_sell_quote_raw": Decimal(10000),
                "latest_sell_liquidity_fraction": Decimal("0.000001"),
            }
        )
    )
    assert not has_dump_hazard(
        _trade(TradeSide.SELL), _feature().model_copy(update={"windows": (metric,)})
    )


def test_hazard_rejects_snapshot_from_another_event_time() -> None:
    from datetime import timedelta

    stale = _feature().model_copy(update={"source_event_at": NOW - timedelta(seconds=1)})
    assert not has_dump_hazard(_trade(TradeSide.SELL), stale)
