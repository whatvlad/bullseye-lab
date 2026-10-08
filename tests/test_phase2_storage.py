from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from memebot.events.models import MarketFeatureSnapshotCreated, TokenTrade, TradeSide
from memebot.intelligence.features.models import RollingWindowMetrics
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import MarketFeatureSnapshotRecord, TokenTradeRecord
from memebot.storage.database.registry import TokenRegistry

MINT = "So11111111111111111111111111111111111111112"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
NOW = datetime(2026, 8, 22, 21, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_trade_and_feature_snapshot_are_persisted_and_queryable() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    trade = TokenTrade(
        event_id=UUID(int=100),
        provider="test",
        source_event_at=NOW,
        source_slot=500,
        mint=MINT,
        signature="1" * 88,
        side=TradeSide.BUY,
        token_amount=Decimal(20),
        quote_amount=Decimal(100),
        quote_asset="SOL",
        market=MARKET,
    )
    metric = RollingWindowMetrics(
        window_seconds=10,
        trade_count=1,
        buy_count=1,
        sell_count=0,
        unique_buyers=0,
        unique_sellers=0,
        buy_volume_quote_raw=Decimal(100),
        sell_volume_quote_raw=Decimal(0),
        total_volume_quote_raw=Decimal(100),
        average_trade_quote_raw=Decimal(100),
        median_trade_quote_raw=Decimal(100),
        largest_buy_quote_raw=Decimal(100),
        flow_imbalance=Decimal(1),
        open_price_raw=Decimal(5),
        close_price_raw=Decimal(5),
        volume_velocity_quote_raw_per_second=Decimal(10),
        transaction_rate_per_second=Decimal("0.1"),
    )
    snapshot = MarketFeatureSnapshotCreated(
        event_id=UUID(int=101),
        provider="rolling_feature_engine",
        source_event_at=NOW,
        source_slot=500,
        mint=MINT,
        trigger_event_id=trade.event_id,
        latest_price_raw=Decimal(5),
        market=MARKET,
        windows=(metric,),
    )

    assert await registry.handle(trade) is True
    assert await registry.handle(snapshot) is True
    assert await registry.handle(snapshot) is False

    async with database.sessions() as session:
        trade_count = await session.scalar(select(func.count()).select_from(TokenTradeRecord))
        snapshot_count = await session.scalar(
            select(func.count()).select_from(MarketFeatureSnapshotRecord)
        )
    queried = await registry.latest_features(MINT)

    assert trade_count == 1
    assert snapshot_count == 1
    assert queried[0]["latest_price_raw"].startswith("5.")
    assert queried[0]["windows"][0]["trade_count"] == 1
    await database.dispose()
