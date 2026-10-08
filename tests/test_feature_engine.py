from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from memebot.events.models import TokenLifecycleChanged, TokenTrade, TradeSide
from memebot.intelligence.features.engine import RollingFeatureEngine
from memebot.market_state import NormalizedMarketState, ReserveSemantics, StateStatus
from memebot.models.market import MarketLifecycle, MarketValidationState

MINT = "So11111111111111111111111111111111111111112"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
WALLET_A = "11111111111111111111111111111111"
WALLET_B = "SysvarRent111111111111111111111111111111111"
WALLET_C = "Vote111111111111111111111111111111111111111"
START = datetime(2026, 8, 22, 20, 0, tzinfo=UTC)


def test_feature_state_capacity_evicts_lru_but_preserves_open_positions():
    engine = RollingFeatureEngine((30,), max_token_states=2)
    seed = _trade(0, event_number=999, side=TradeSide.BUY, token=10, quote=100, wallet=WALLET_A)
    engine.ingest_trade(seed)
    engine.pin_mint(MINT)
    engine.ingest_trade(seed.model_copy(update={"mint": WALLET_B, "event_id": UUID(int=1000)}))
    engine.ingest_trade(seed.model_copy(update={"mint": WALLET_C, "event_id": UUID(int=1001)}))
    assert len(engine._states) == 2
    assert MINT in engine._states
    assert WALLET_B not in engine._states
    assert engine.evicted_token_states == 1


def test_subsecond_trade_has_current_features_without_duplicate_persistence() -> None:
    engine = RollingFeatureEngine((30,), snapshot_interval_seconds=1)
    first = _trade(0, event_number=901, side=TradeSide.SELL, token=10, quote=100, wallet=WALLET_A)
    second = _trade(
        0, event_number=902, side=TradeSide.SELL, token=10, quote=101, wallet=WALLET_A
    ).model_copy(update={"source_event_at": START + timedelta(milliseconds=100)})
    assert engine.ingest_trade(first) is not None
    assert engine.ingest_trade(second) is None
    current = engine.current_snapshot(second)
    assert current is not None
    assert current.source_event_at == second.source_event_at
    assert current.windows[0].trade_count == 2


def test_reserve_spot_is_used_instead_of_trade_average() -> None:
    engine = RollingFeatureEngine((30,), snapshot_interval_seconds=1)
    trade = _trade(
        0, event_number=903, side=TradeSide.BUY, token=10, quote=100, wallet=WALLET_A
    ).model_copy(
        update={
            "normalized_state": NormalizedMarketState(
                virtual_quote=400,
                virtual_token=100,
                reserve_semantics=ReserveSemantics.POST_TRADE,
                state_quality=StateStatus.INCOMPLETE,
                continuity_status="FIRST_OBSERVATION",
            )
        }
    )
    snapshot = engine.ingest_trade(trade)
    assert snapshot is not None
    assert snapshot.latest_price_raw == Decimal(4)


def test_lifecycle_event_cannot_refresh_the_last_trade_price_clock() -> None:
    engine = RollingFeatureEngine((120,), snapshot_interval_seconds=1)
    trade = _trade(0, event_number=904, side=TradeSide.BUY, token=10, quote=100, wallet=WALLET_A)
    trade = trade.model_copy(update={"ingested_at": START, "provider_received_at": START})
    engine.ingest_trade(trade)
    changed = START + timedelta(seconds=60)
    snapshot = engine.ingest_lifecycle(
        TokenLifecycleChanged(
            mint=MINT,
            provider="test",
            source_event_at=changed,
            ingested_at=changed,
            provider_received_at=changed,
            lifecycle=MarketLifecycle.FINAL_STRETCH,
            validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
            market=MARKET,
        )
    )
    assert snapshot is not None
    assert snapshot.price_evidence["source_timestamp"] == START
    assert snapshot.price_evidence["price_age_ms"] == 60000
    assert snapshot.price_evidence["feed_age_ms"] == 60000


def _trade(
    second: int,
    *,
    event_number: int,
    side: TradeSide,
    token: int,
    quote: int,
    wallet: str,
    reserve: int | None = None,
) -> TokenTrade:
    return TokenTrade(
        event_id=UUID(int=event_number),
        provider="replay",
        source_event_at=START + timedelta(seconds=second),
        provider_received_at=START + timedelta(seconds=second, milliseconds=10),
        ingested_at=START + timedelta(seconds=second, milliseconds=20),
        source_slot=100 + second,
        source_sequence=event_number,
        source_signature=str(event_number) * 32,
        mint=MINT,
        signature=str(event_number) * 32,
        side=side,
        token_amount=Decimal(token),
        quote_amount=Decimal(quote),
        quote_asset="SOL",
        wallet=wallet,
        market=MARKET,
        real_quote_reserves=reserve,
        normalized_state=NormalizedMarketState(
            state_source="synthetic_fixture",
            reserve_semantics=ReserveSemantics.POST_TRADE,
            state_quality=StateStatus.INCOMPLETE,
            continuity_status="FIRST_OBSERVATION",
            virtual_quote=quote,
            virtual_token=token,
            quote_reserve=reserve,
        ),
    )


def test_rolling_metrics_cover_flow_velocity_and_acceleration() -> None:
    engine = RollingFeatureEngine((10,), snapshot_interval_seconds=1)
    events = [
        _trade(0, event_number=1, side=TradeSide.BUY, token=10, quote=100, wallet=WALLET_A),
        _trade(5, event_number=2, side=TradeSide.BUY, token=10, quote=200, wallet=WALLET_B),
        _trade(9, event_number=3, side=TradeSide.SELL, token=10, quote=150, wallet=WALLET_C),
    ]

    snapshots = [snapshot for event in events if (snapshot := engine.ingest_trade(event))]
    metric = snapshots[-1].windows[0]

    assert metric.trade_count == 3
    assert metric.buy_count == 2
    assert metric.sell_count == 1
    assert metric.unique_buyers == 2
    assert metric.unique_sellers == 1
    assert metric.buy_volume_quote_raw == 300
    assert metric.sell_volume_quote_raw == 150
    assert metric.average_trade_quote_raw == 150
    assert metric.median_trade_quote_raw == 150
    assert metric.largest_buy_quote_raw == 200
    assert metric.buy_sell_count_ratio == 2
    assert metric.buy_sell_volume_ratio == 2
    assert metric.flow_imbalance == Decimal(1) / 3
    assert metric.open_price_raw == 10
    assert metric.close_price_raw == 15
    assert metric.price_change_percent == 50
    assert metric.price_velocity_percent_per_second == Decimal(50) / 9
    assert metric.volume_velocity_quote_raw_per_second == 45
    assert metric.volume_acceleration_quote_raw_per_second2 == 10
    assert metric.transaction_rate_acceleration_per_second2 == Decimal("0.04")
    assert metric.unique_buyer_rate_acceleration_per_second2 == 0
    assert metric.buy_pressure_acceleration_per_second == -Decimal(6) / 35
    # The first half has one observation: its velocity is unknown, not zero.
    assert metric.price_acceleration_percent_per_second2 is None


def test_replay_is_deterministic_and_duplicate_safe() -> None:
    events = [
        _trade(0, event_number=10, side=TradeSide.BUY, token=10, quote=100, wallet=WALLET_A),
        _trade(2, event_number=11, side=TradeSide.SELL, token=10, quote=90, wallet=WALLET_B),
        _trade(6, event_number=12, side=TradeSide.BUY, token=10, quote=140, wallet=WALLET_C),
    ]

    def replay() -> list[dict[str, object]]:
        engine = RollingFeatureEngine((5, 10), snapshot_interval_seconds=1)
        output = []
        for event in events:
            snapshot = engine.ingest_trade(event)
            if snapshot is not None:
                output.append(snapshot.model_dump(mode="json"))
        assert engine.ingest_trade(events[-1]) is None
        return output

    assert replay() == replay()


def test_out_of_order_events_are_bounded_and_sorted() -> None:
    engine = RollingFeatureEngine((10,), max_lateness_seconds=5)
    first = _trade(0, event_number=20, side=TradeSide.BUY, token=10, quote=100, wallet=WALLET_A)
    fourth = _trade(4, event_number=21, side=TradeSide.BUY, token=10, quote=120, wallet=WALLET_B)
    second = _trade(2, event_number=22, side=TradeSide.SELL, token=10, quote=80, wallet=WALLET_C)
    sixth = _trade(6, event_number=23, side=TradeSide.BUY, token=10, quote=150, wallet=WALLET_A)
    too_late = _trade(0, event_number=24, side=TradeSide.SELL, token=10, quote=999, wallet=WALLET_C)

    assert engine.ingest_trade(first) is not None
    assert engine.ingest_trade(fourth) is not None
    assert engine.ingest_trade(second) is None
    snapshot = engine.ingest_trade(sixth)
    assert snapshot is not None
    assert snapshot.windows[0].trade_count == 4
    assert snapshot.windows[0].open_price_raw == 10
    assert snapshot.windows[0].close_price_raw == 15
    assert engine.ingest_trade(too_late) is None


def test_lifecycle_features_are_included_without_inventing_trades() -> None:
    engine = RollingFeatureEngine((5, 10))
    lifecycle = TokenLifecycleChanged(
        event_id=UUID(int=30),
        provider="replay",
        source_event_at=START,
        ingested_at=START,
        source_slot=200,
        mint=MINT,
        lifecycle=MarketLifecycle.FINAL_STRETCH,
        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        bonding_progress_percent=Decimal("82.5"),
        market=MARKET,
    )

    snapshot = engine.ingest_lifecycle(lifecycle)

    assert snapshot is not None
    assert snapshot.lifecycle == MarketLifecycle.FINAL_STRETCH
    assert snapshot.bonding_progress_percent == Decimal("82.5")
    assert all(window.trade_count == 0 for window in snapshot.windows)
    assert snapshot.latest_price_raw is None


def test_graduation_and_dump_features_are_point_in_time() -> None:
    engine = RollingFeatureEngine((30,), snapshot_interval_seconds=1)
    events = [
        _trade(
            index,
            event_number=40 + index,
            side=TradeSide.SELL if index in {3, 5} else TradeSide.BUY,
            token=10,
            quote=(800 if index == 5 else 100 + index * 10),
            wallet=(WALLET_A, WALLET_B, WALLET_C)[index % 3],
            reserve=1_000 + index * 100,
        )
        for index in range(6)
    ]
    snapshots = [snapshot for event in events if (snapshot := engine.ingest_trade(event))]
    metric = snapshots[-1].windows[0]

    assert metric.quote_reserve_change_raw == 500
    assert metric.quote_reserve_velocity_raw_per_second == 100
    assert metric.buyer_volume_hhi is not None
    assert Decimal(0) < metric.buyer_volume_hhi <= Decimal(1)
    assert metric.buyer_wallet_attribution_percent == 100
    assert metric.largest_buyer_volume_share is not None
    assert metric.latest_price_return_percent is not None
