from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from memebot.events.models import (
    DomainEvent,
    MarketFeatureSnapshotCreated,
    PaperOrderCompleted,
    StrategyDecisionCreated,
    TokenDiscovered,
    TokenLifecycleChanged,
    TokenRiskAssessed,
    TokenTrade,
    TradeSide,
)
from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.market import LaunchVenue, MarketLifecycle, MarketValidationState
from memebot.models.paper import PositionEffect
from memebot.models.risk import RiskResult
from memebot.models.strategy import ScoreResult, StrategyDecisionAction, StrategyRegime
from memebot.paper.execution import ExecutionPolicy, PaperFillSimulator
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.price.base import QuotePrice
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.outcomes import OutcomeRecorder
from memebot.storage.database.registry import TokenRegistry
from memebot.strategies.presets import initial_strategy_presets
from standard_evidence import approved_state

MINT = "11111111111111111111111111111111"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
NOW = datetime(2026, 8, 23, 1, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_skipped_outcome_tracks_horizons_mfe_mae_and_lifecycle() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    outcomes = OutcomeRecorder(database.sessions)
    configurations = initial_strategy_presets()
    await registry.ensure_strategy_configurations(configurations)
    aggressive = next(item for item in configurations if item.key == "aggressive")

    await _ingest(registry, outcomes, _discovery())
    feature = MarketFeatureSnapshotCreated(
        event_id=UUID(int=10),
        provider="test",
        source_event_at=NOW,
        mint=MINT,
        trigger_event_id=UUID(int=9),
        lifecycle=MarketLifecycle.BONDING_CURVE,
        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        market=MARKET,
        latest_price_raw=Decimal(2),
        windows=(),
    )
    risk = TokenRiskAssessed(
        event_id=UUID(int=11),
        provider="test",
        source_event_at=NOW,
        mint=MINT,
        trigger_event_id=UUID(int=9),
        market=MARKET,
        result=RiskResult(
            allowed=True,
            risk_score=Decimal(10),
            data_completeness_percent=Decimal(100),
        ),
    )
    decision = StrategyDecisionCreated(
        event_id=UUID(int=12),
        provider="test",
        source_event_at=NOW,
        mint=MINT,
        strategy_key="aggressive",
        strategy_version_id=aggressive.version_id,
        active_strategy=True,
        action=StrategyDecisionAction.WATCH,
        regime=StrategyRegime.BONDING_CURVE,
        risk_event_id=risk.event_id,
        feature_event_id=feature.event_id,
        score=ScoreResult(
            final_score=Decimal(55),
            component_completeness_percent=Decimal(70),
            components=(),
        ),
        reasons=("score_at_or_above_watch_threshold:50",),
    )
    await _ingest(registry, outcomes, feature)
    await _ingest(registry, outcomes, risk)
    await _ingest(registry, outcomes, decision)
    await _ingest(registry, outcomes, _trade(UUID(int=13), 30, Decimal(3)))
    await _ingest(registry, outcomes, _trade(UUID(int=14), 60, Decimal(1)))
    await _ingest(
        registry,
        outcomes,
        _lifecycle(UUID(int=15), 90, MarketLifecycle.GRADUATION),
    )
    await _ingest(
        registry,
        outcomes,
        _lifecycle(UUID(int=16), 120, MarketLifecycle.DEAD_OR_ILLIQUID),
    )

    recorded = (await outcomes.latest_decisions(limit=1))[0]
    assert recorded["execution_status"] == "watch"
    assert Decimal(recorded["mfe_percent"]) == Decimal(50)
    assert Decimal(recorded["mae_percent"]) == Decimal(-50)
    assert recorded["horizon_returns"]["30"]["return_percent"] == "50.0"
    assert recorded["horizon_returns"]["60"]["return_percent"] == "-50.0"
    assert recorded["graduated"] is True
    assert recorded["liquidity_collapsed"] is True
    await database.dispose()


@pytest.mark.asyncio
async def test_taken_trade_outcome_closes_and_disappears_from_open_positions() -> None:
    database = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await database.create_schema_for_tests()
    registry = TokenRegistry(database.sessions)
    outcomes = OutcomeRecorder(database.sessions)
    await _ingest(registry, outcomes, _discovery())
    portfolio = await registry.ensure_default_paper_portfolio(
        initial_cash=Decimal(1000), currency="USDT"
    )
    simulator = _simulator()
    buy_result = simulator.simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(100),
        signal_at=NOW,
        decision_at=NOW,
    )
    buy = PaperOrderCompleted(
        event_id=UUID(int=21),
        provider="test",
        source_event_at=NOW,
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        trigger_event_id=UUID(int=20),
        strategy_key="manual",
        market=MARKET,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        result=buy_result,
    )
    await _ingest(registry, outcomes, buy)
    position = await registry.open_position(MINT)
    assert position is not None
    sell_result = simulator.simulate_sell(
        _market(),
        _quote(),
        token_amount_raw=position.token_quantity_raw,
        position_effect=PositionEffect.CLOSE,
        exit_reason="manual",
        signal_at=NOW + timedelta(seconds=5),
        decision_at=NOW + timedelta(seconds=5),
    )
    sell = PaperOrderCompleted(
        event_id=UUID(int=22),
        provider="test",
        source_event_at=NOW + timedelta(seconds=5),
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        trigger_event_id=UUID(int=20),
        strategy_key="manual",
        market=MARKET,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        result=sell_result,
    )
    await _ingest(registry, outcomes, sell)

    report = await registry.paper_portfolio_report()
    trade = (await outcomes.latest_trades(limit=1))[0]
    assert report is not None
    assert report["positions"] == []
    assert trade["status"] == "closed"
    assert trade["exit_reason"] == "manual"
    assert trade["holding_seconds"] == 5

    second_buy_result = simulator.simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(75),
        signal_at=NOW + timedelta(seconds=6),
        decision_at=NOW + timedelta(seconds=6),
    )
    second_buy = buy.model_copy(
        update={
            "event_id": UUID(int=23),
            "source_event_at": NOW + timedelta(seconds=6),
            "result": second_buy_result,
        }
    )
    await _ingest(registry, outcomes, second_buy)
    second_position = await registry.open_position(MINT)
    assert second_position is not None
    second_sell_result = simulator.simulate_sell(
        _market(),
        _quote(),
        token_amount_raw=second_position.token_quantity_raw,
        position_effect=PositionEffect.CLOSE,
        exit_reason="manual_second_cycle",
        signal_at=NOW + timedelta(seconds=10),
        decision_at=NOW + timedelta(seconds=10),
    )
    second_sell = sell.model_copy(
        update={
            "event_id": UUID(int=24),
            "source_event_at": NOW + timedelta(seconds=10),
            "result": second_sell_result,
        }
    )
    await _ingest(registry, outcomes, second_sell)

    trades = await outcomes.latest_trades(limit=2)
    assert [item["status"] for item in trades] == ["closed", "closed"]
    assert trades[0]["exit_reason"] == "manual_second_cycle"
    await database.dispose()


async def _ingest(
    registry: TokenRegistry,
    outcomes: OutcomeRecorder,
    event: DomainEvent,
) -> None:
    assert await registry.handle(event)
    await outcomes.handle(event)


def _discovery() -> TokenDiscovered:
    return TokenDiscovered(
        event_id=UUID(int=1),
        provider="test",
        source_event_at=NOW,
        mint=MINT,
        name="Outcome Coin",
        symbol="OUT",
        launch_venue=LaunchVenue.PUMP_FUN,
    )


def _trade(event_id: UUID, seconds: int, price: Decimal) -> TokenTrade:
    return TokenTrade(
        event_id=event_id,
        provider="test",
        source_event_at=NOW + timedelta(seconds=seconds),
        mint=MINT,
        signature=str(event_id).replace("-", "") * 2,
        side=TradeSide.BUY,
        token_amount=Decimal(10),
        quote_amount=price * Decimal(10),
        amounts_are_raw=True,
        quote_asset=WRAPPED_SOL_MINT,
        market=MARKET,
    )


def _lifecycle(event_id: UUID, seconds: int, lifecycle: MarketLifecycle) -> TokenLifecycleChanged:
    return TokenLifecycleChanged(
        event_id=event_id,
        provider="test",
        source_event_at=NOW + timedelta(seconds=seconds),
        mint=MINT,
        lifecycle=lifecycle,
        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        market=MARKET,
    )


def _simulator() -> PaperFillSimulator:
    return PaperFillSimulator(
        ExecutionPolicy(
            venue_fee_bps=Decimal(0),
            latency_slippage_bps=Decimal(0),
            network_fee_sol=Decimal(0),
            priority_fee_sol=Decimal(0),
            compute_latency_ms=0,
            submission_latency_ms=0,
            max_market_staleness_seconds=10,
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
        source_slot=1,
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
