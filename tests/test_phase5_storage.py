from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from memebot.events.models import (
    PaperOrderCompleted,
    TokenDiscovered,
    TokenLifecycleChanged,
    TokenTrade,
    TradeSide,
)
from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.market import (
    LaunchVenue,
    MarketLifecycle,
    MarketValidationState,
)
from memebot.models.paper import PositionEffect
from memebot.paper.execution import ExecutionPolicy, PaperFillSimulator
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.price.base import QuotePrice
from memebot.providers.solana.pump_idl import NATIVE_SOL_MINT, WRAPPED_SOL_MINT
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.registry import TokenRegistry
from standard_evidence import approved_state

MINT = "11111111111111111111111111111111"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
NOW = datetime(2026, 8, 22, 23, 50, tzinfo=UTC)


def _simulator() -> PaperFillSimulator:
    return PaperFillSimulator(
        ExecutionPolicy(
            venue_fee_bps=Decimal(0),
            latency_slippage_bps=Decimal(0),
            network_fee_sol=Decimal(0),
            priority_fee_sol=Decimal(0),
            compute_latency_ms=0,
            submission_latency_ms=0,
            max_market_staleness_seconds=5,
            max_quote_price_staleness_seconds=90,
        )
    )


def _market() -> ExecutionMarketSnapshot:
    return ExecutionMarketSnapshot(
        mint=MINT,
        market=MARKET,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        observed_at=NOW,
        source_slot=1100,
        observed_price_raw=Decimal("0.1"),
        quote_asset=WRAPPED_SOL_MINT,
        real_token_reserves_raw=100_000_000_000,
        real_quote_reserves_raw=10_000_000_000,
        virtual_token_reserves_raw=100_000_000_000,
        virtual_quote_reserves_raw=10_000_000_000,
        normalized_state=approved_state(),
        is_mayhem_mode=False,
    )


def _quote() -> QuotePrice:
    return QuotePrice(
        quote_asset=WRAPPED_SOL_MINT,
        portfolio_currency="USDT",
        price=Decimal(100),
        provenance=ProviderProvenance(
            provider="test",
            observed_at=NOW,
            confidence=DataConfidence.HIGH,
        ),
    )


@pytest.mark.asyncio
async def test_buy_partial_sell_and_portfolio_accounting_reconcile() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    portfolio = await registry.ensure_default_paper_portfolio(
        initial_cash=Decimal(1000), currency="USDT"
    )
    buy_result = _simulator().simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(100),
        signal_at=NOW,
        decision_at=NOW,
    )
    buy = PaperOrderCompleted(
        event_id=UUID(int=501),
        provider="paper_test",
        source_event_at=NOW,
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        trigger_event_id=UUID(int=500),
        decision_event_id=UUID(int=499),
        strategy_key="aggressive",
        market=MARKET,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        result=buy_result,
    )
    assert await registry.handle(buy) is True
    position = await registry.open_position(MINT)
    assert position is not None
    full_mark = (
        _simulator()
        .simulate_sell(
            _market(),
            _quote(),
            token_amount_raw=position.token_quantity_raw,
            position_effect=PositionEffect.CLOSE,
            exit_reason="execution_mark",
            signal_at=NOW,
            decision_at=NOW,
        )
        .fill
    )
    assert full_mark is not None
    await registry.observe_open_position_price(
        position.position_id,
        full_mark.actual_fill_price_raw,
        observed_at=NOW,
        execution_fill=full_mark,
    )
    state = await registry.paper_risk_snapshot(MINT, as_of=NOW)
    assert state is not None and state.execution_marks_valid
    assert state.unrealized_pnl == (
        full_mark.gross_portfolio_amount
        - full_mark.total_fee_portfolio
        - position.remaining_cost_basis
    )
    stale_state = await registry.paper_risk_snapshot(MINT, as_of=NOW + timedelta(seconds=6))
    assert stale_state is not None and not stale_state.execution_marks_valid
    await registry.handle(
        TokenTrade(
            provider="test",
            source_event_at=NOW,
            mint=MINT,
            signature="c" * 64,
            market=MARKET,
            side=TradeSide.BUY,
            token_amount=Decimal(1),
            quote_amount=Decimal(99999999),
            quote_asset=WRAPPED_SOL_MINT,
        )
    )
    after_trade = await registry.open_position(MINT)
    assert after_trade is not None
    assert after_trade.peak_price_raw == position.peak_price_raw

    sell_result = _simulator().simulate_sell(
        _market(),
        _quote(),
        token_amount_raw=position.token_quantity_raw / Decimal(2),
        position_effect=PositionEffect.PARTIAL_CLOSE,
        exit_reason="partial_take_profit",
        signal_at=NOW,
        decision_at=NOW,
    )
    sell = PaperOrderCompleted(
        event_id=UUID(int=502),
        provider="paper_test",
        source_event_at=NOW,
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        trigger_event_id=UUID(int=503),
        strategy_key="aggressive",
        market=MARKET,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        result=sell_result,
    )
    invalid_close = sell.model_copy(
        update={"result": sell_result.model_copy(update={"position_effect": PositionEffect.CLOSE})}
    )
    with pytest.raises(ValueError, match="entire remaining quantity"):
        await registry.handle(invalid_close)
    unchanged = await registry.open_position(MINT)
    assert unchanged is not None
    assert unchanged.remaining_cost_basis == position.remaining_cost_basis
    assert unchanged.token_quantity_raw == position.token_quantity_raw
    assert await registry.handle(sell) is True

    report = await registry.paper_portfolio_report()
    orders = await registry.latest_paper_orders()
    updated = await registry.open_position(MINT)

    assert report is not None
    assert report["accounting_reconciled"] is True
    assert report["accounting_difference"] == "0E-8"
    assert len(orders) == 2
    assert updated is not None
    assert updated.partial_take_profit_taken is True
    assert updated.token_quantity_raw < position.token_quantity_raw
    partial_state = await registry.paper_risk_snapshot(MINT, as_of=NOW)
    assert partial_state is not None and not partial_state.execution_marks_valid
    await database.dispose()


@pytest.mark.asyncio
async def test_zero_quantity_partial_exit_race_is_reconciled_as_closed() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    portfolio = await registry.ensure_default_paper_portfolio(
        initial_cash=Decimal(1000), currency="USDT"
    )
    buy_result = _simulator().simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(100),
        signal_at=NOW,
        decision_at=NOW,
    )
    # This legacy recovery scenario needs two exact half sells. SPL raw units
    # are integers, so use an even entry quantity instead of fractional halves.
    assert buy_result.fill is not None
    even_quantity = (buy_result.fill.token_amount_raw // 2) * 2
    buy_result = buy_result.model_copy(
        update={
            "fill": buy_result.fill.model_copy(
                update={
                    "token_amount_raw": even_quantity,
                    "actual_fill_price_raw": buy_result.fill.gross_quote_amount_raw / even_quantity,
                }
            )
        }
    )
    buy = PaperOrderCompleted(
        event_id=UUID(int=601),
        provider="paper_test",
        source_event_at=NOW,
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        trigger_event_id=UUID(int=600),
        strategy_key="balanced",
        market=MARKET,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        result=buy_result,
    )
    assert await registry.handle(buy)
    position = await registry.open_position(MINT)
    assert position is not None
    duplicate_half_sell = _simulator().simulate_sell(
        _market(),
        _quote(),
        token_amount_raw=position.token_quantity_raw / Decimal(2),
        position_effect=PositionEffect.PARTIAL_CLOSE,
        exit_reason="partial_take_profit",
        signal_at=NOW,
        decision_at=NOW,
    )
    for event_id in (602, 603):
        assert await registry.handle(
            PaperOrderCompleted(
                event_id=UUID(int=event_id),
                provider="paper_test",
                source_event_at=NOW,
                portfolio_id=portfolio.portfolio_id,
                mint=MINT,
                trigger_event_id=UUID(int=event_id + 10),
                strategy_key="balanced",
                market=MARKET,
                venue=LaunchVenue.PUMP_FUN,
                lifecycle=MarketLifecycle.BONDING_CURVE,
                result=duplicate_half_sell,
            )
        )

    dust = await registry.open_position(MINT)
    assert dust is not None and dust.token_quantity_raw == 0
    assert await registry.reconcile_zero_quantity_positions(closed_at=NOW) == 1
    assert await registry.open_position(MINT) is None
    await database.dispose()


@pytest.mark.asyncio
async def test_native_sol_market_is_normalized_for_paper_execution() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    await registry.handle(
        TokenDiscovered(
            provider="test",
            source_event_at=NOW,
            mint=MINT,
            launch_venue=LaunchVenue.PUMP_FUN,
        )
    )
    await registry.handle(
        TokenLifecycleChanged(
            provider="test",
            source_event_at=NOW,
            mint=MINT,
            lifecycle=MarketLifecycle.BONDING_CURVE,
            validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
            market=MARKET,
            quote_mint=NATIVE_SOL_MINT,
        )
    )
    await registry.handle(
        TokenTrade(
            provider="test",
            source_event_at=NOW,
            mint=MINT,
            signature="1" * 88,
            side=TradeSide.BUY,
            token_amount=Decimal(1_000_000),
            quote_amount=Decimal(10_000),
            quote_asset=NATIVE_SOL_MINT,
            quote_mint=NATIVE_SOL_MINT,
            market=MARKET,
            real_token_reserves=100_000_000,
            real_quote_reserves=10_000_000,
            virtual_token_reserves=100_000_000,
            virtual_quote_reserves=10_000_000,
        )
    )

    context = await registry.paper_market_context(MINT, as_of=NOW)

    assert context is not None
    assert context.quote_asset == WRAPPED_SOL_MINT
    await database.dispose()
