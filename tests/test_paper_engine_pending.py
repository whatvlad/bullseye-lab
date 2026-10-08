from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

import memebot.paper.engine as engine_module
from memebot.core.config import Settings
from memebot.events.models import (
    DomainEvent,
    PaperOrderCompleted,
    StrategyDecisionCreated,
    TokenTrade,
    TradeSide,
)
from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import PaperOrderStatus
from memebot.models.strategy import (
    ScoreComponent,
    ScoreResult,
    StrategyDecisionAction,
    StrategyRegime,
)
from memebot.paper.engine import PaperTradingEngine
from memebot.paper.models import (
    ExecutionMarketSnapshot,
    PortfolioRiskSnapshot,
    PortfolioSnapshot,
    PositionSnapshot,
)
from memebot.providers.price.base import QuotePrice
from memebot.providers.price.coingecko import QuotePriceError
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.storage.database.control import TradingControlSnapshot
from memebot.storage.database.pending import PendingPaperAction
from standard_evidence import approved_evidence, approved_state, atomic_market

MINT = "So11111111111111111111111111111111111111112"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
NOW = datetime(2026, 8, 23, 2, 0, tzinfo=UTC)


def _sizing_engine() -> PaperTradingEngine:
    async def publish(event: DomainEvent) -> int:
        return 1

    return PaperTradingEngine(
        Settings(_env_file=None, paper_compute_latency_ms=0, paper_submission_latency_ms=0),
        SimpleNamespace(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        publish,
        entry_thresholds={"balanced": Decimal(60)},
    )


def test_v5_sizing_does_not_amplify_uncalibrated_score() -> None:
    engine = _sizing_engine()
    portfolio = PortfolioSnapshot(
        UUID(int=100), "USDT", Decimal(1000), Decimal(1000), Decimal(0), 0
    )
    control = TradingControlSnapshot(
        True,
        "balanced",
        Decimal(8),
        Decimal(20),
        5,
        Decimal(20),
        Decimal(25),
        Decimal(8),
        1800,
    )

    for score in (60, 70, 85):
        assert engine._position_size(portfolio, Decimal(score), "balanced", control) == Decimal(
            "16.66666667"
        )


def test_v3_stagnation_exit_requires_time_no_excursion_and_non_positive_mark() -> None:
    engine = _sizing_engine()

    assert engine._is_stagnant(120, Decimal(4), Decimal(-1)) is True
    assert engine._is_stagnant(119, Decimal(4), Decimal(-1)) is False
    assert engine._is_stagnant(120, Decimal(6), Decimal(-1)) is False
    assert engine._is_stagnant(120, Decimal(4), Decimal(1)) is False


@pytest.mark.asyncio
async def test_fresh_trade_executes_persistent_manual_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine_module, "utc_now", lambda: NOW)
    portfolio = PortfolioSnapshot(
        portfolio_id=UUID(int=1),
        currency="USDT",
        initial_cash=Decimal(1000),
        cash_balance=Decimal(500),
        realized_pnl=Decimal(0),
        open_position_count=1,
    )
    position = PositionSnapshot(
        position_id=UUID(int=2),
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        strategy_key="conservative",
        market=MARKET,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        token_quantity_raw=Decimal(1_000_000),
        remaining_cost_basis=Decimal(100),
        realized_pnl=Decimal(0),
        entry_price_raw=Decimal("0.1"),
        peak_price_raw=Decimal("0.1"),
        opened_at=NOW - timedelta(minutes=1),
        partial_take_profit_taken=False,
    )
    market = atomic_market(
        ExecutionMarketSnapshot(
            mint=MINT,
            market=MARKET,
            venue=LaunchVenue.PUMP_FUN,
            lifecycle=MarketLifecycle.BONDING_CURVE,
            observed_at=NOW,
            source_slot=100,
            observed_price_raw=Decimal("0.1"),
            quote_asset=WRAPPED_SOL_MINT,
            real_token_reserves_raw=100_000_000_000,
            real_quote_reserves_raw=10_000_000_000,
            virtual_token_reserves_raw=100_000_000_000,
            virtual_quote_reserves_raw=10_000_000_000,
        )
    )
    action = PendingPaperAction(
        id=UUID(int=3),
        portfolio_id=portfolio.portfolio_id,
        mint=MINT,
        action="manual_close",
        expires_at=NOW + timedelta(seconds=30),
        decision=None,
        requested_by_user_id=123,
    )
    finished: list[dict[str, object]] = []

    class Registry:
        async def active_paper_portfolio(self) -> PortfolioSnapshot:
            return portfolio

        async def open_position(self, mint: str) -> PositionSnapshot:
            assert mint == MINT
            return position

        async def paper_market_context(
            self, mint: str, *, as_of: datetime
        ) -> ExecutionMarketSnapshot:
            assert mint == MINT and as_of == NOW
            return market

    class Pending:
        async def pending_for_mint(self, mint: str, *, action: str) -> PendingPaperAction | None:
            return action_record if action == "manual_close" else None

        async def finish(self, action_id: UUID, **values: object) -> None:
            finished.append({"action_id": action_id, **values})

    class Quotes:
        async def quote_price(self, portfolio_currency: str) -> QuotePrice:
            return QuotePrice(
                quote_asset=WRAPPED_SOL_MINT,
                portfolio_currency=portfolio_currency,
                price=Decimal(100),
                provenance=ProviderProvenance(
                    provider="test",
                    observed_at=NOW,
                    confidence=DataConfidence.HIGH,
                ),
            )

        async def close(self) -> None:
            return None

    action_record = action
    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        return 1

    engine = PaperTradingEngine(
        Settings(_env_file=None, paper_compute_latency_ms=0, paper_submission_latency_ms=0),
        Registry(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        Pending(),  # type: ignore[arg-type]
        Quotes(),
        publish,
        entry_thresholds={"conservative": Decimal(80)},
    )
    trade = TokenTrade(
        event_id=UUID(int=4),
        provider="test",
        source_event_at=NOW,
        mint=MINT,
        signature="a" * 64,
        side=TradeSide.BUY,
        token_amount=Decimal(100),
        quote_amount=Decimal(10),
        amounts_are_raw=True,
        quote_asset=WRAPPED_SOL_MINT,
        market=MARKET,
    )

    await engine.on_trade(trade)

    order = next(item for item in published if isinstance(item, PaperOrderCompleted))
    assert order.result.status == PaperOrderStatus.FILLED
    assert order.result.exit_reason == "manual_paper_sell_on_fresh_trade"
    assert finished[0]["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("model_action", [None, "hold", "timeout"])
@pytest.mark.parametrize(
    "failure", ["no_stream", "no_rpc", "disagreement", "no_quote", "no_context"]
)
async def test_position_monitor_closes_stop_without_new_trade(
    monkeypatch: pytest.MonkeyPatch,
    model_action: str | None,
    failure: str,
) -> None:
    monkeypatch.setattr(engine_module, "utc_now", lambda: NOW)
    portfolio = PortfolioSnapshot(UUID(int=101), "USDT", Decimal(1000), Decimal(900), Decimal(0), 1)
    position = PositionSnapshot(
        UUID(int=102),
        portfolio.portfolio_id,
        MINT,
        "balanced",
        MARKET,
        LaunchVenue.PUMP_FUN,
        MarketLifecycle.BONDING_CURVE,
        Decimal(1_000_000),
        Decimal(100),
        Decimal(0),
        Decimal("0.1"),
        Decimal("0.1"),
        NOW - timedelta(minutes=1),
        False,
    )
    stale = ExecutionMarketSnapshot(
        MINT,
        MARKET,
        LaunchVenue.PUMP_FUN,
        MarketLifecycle.BONDING_CURVE,
        NOW - timedelta(minutes=1),
        100,
        Decimal("0.1"),
        WRAPPED_SOL_MINT,
        100_000_000_000,
        10_000_000_000,
        100_000_000_000,
        10_000_000_000,
    )
    fresh = atomic_market(
        ExecutionMarketSnapshot(
            MINT,
            MARKET,
            LaunchVenue.PUMP_FUN,
            MarketLifecycle.BONDING_CURVE,
            NOW,
            101,
            Decimal("0.07"),
            WRAPPED_SOL_MINT,
            100_000_000_000,
            7_000_000_000,
            100_000_000_000,
            7_000_000_000,
        )
    )
    fresh = replace(
        fresh,
        price_source="stream_reserves" if failure == "no_rpc" else "rpc_reserves",
        feed_timestamp=NOW - timedelta(minutes=5) if failure == "no_stream" else NOW,
        received_timestamp=NOW,
        rpc_state="degraded" if failure == "no_rpc" else "healthy",
        price_source_disagreement_pct=Decimal(73) if failure == "disagreement" else None,
        data_quality="test",
        feed_timestamp_estimated=False,
    )
    observations: list[Decimal] = []

    class Registry:
        async def reconcile_zero_quantity_positions(self) -> int:
            return 0

        async def active_paper_portfolio(self) -> PortfolioSnapshot:
            return portfolio

        async def open_positions(self) -> list[PositionSnapshot]:
            return [position]

        async def open_position(self, mint: str) -> PositionSnapshot:
            return position

        async def paper_market_context(
            self, mint: str, *, as_of: datetime
        ) -> ExecutionMarketSnapshot | None:
            return None if failure == "no_context" else stale

        async def observe_open_position_price(
            self,
            position_id: UUID,
            price: Decimal,
            *,
            observed_at: datetime,
            execution_fill: object = None,
        ) -> None:
            observations.append(price)

        async def paper_risk_snapshot(self, mint: str, *, as_of: datetime) -> PortfolioRiskSnapshot:
            return PortfolioRiskSnapshot(
                portfolio.portfolio_id,
                portfolio.initial_cash,
                position.remaining_cost_basis,
                Decimal(-30),
                Decimal(0),
                0,
                None,
                None,
            )

    class Controls:
        async def get(self) -> TradingControlSnapshot:
            return TradingControlSnapshot(
                False,
                "balanced",
                Decimal(1),
                Decimal(2),
                5,
                Decimal(20),
                Decimal(25),
                Decimal(8),
                1800,
            )

    class Refresher:
        rpc_unavailable = failure == "no_rpc"

        async def refresh(self, market: ExecutionMarketSnapshot) -> ExecutionMarketSnapshot:
            if self.rpc_unavailable:
                self.rpc_unavailable = False
                return fresh
            if failure == "no_rpc":
                return replace(fresh, rpc_state="healthy", price_source="rpc_reserves")
            return fresh

    class Quotes:
        unavailable = failure == "no_quote"

        async def quote_price(self, portfolio_currency: str) -> QuotePrice:
            if self.unavailable:
                self.unavailable = False
                raise QuotePriceError("test outage")
            return QuotePrice(
                quote_asset=WRAPPED_SOL_MINT,
                portfolio_currency=portfolio_currency,
                price=Decimal(100),
                provenance=ProviderProvenance(
                    provider="test", observed_at=NOW, confidence=DataConfidence.HIGH
                ),
            )

        async def close(self) -> None:
            return None

    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        return 1

    class Model:
        async def exit(self, *args: object) -> object:
            pytest.fail(f"emergency stop must bypass model {model_action}")

    engine = PaperTradingEngine(
        Settings(_env_file=None, paper_compute_latency_ms=0, paper_submission_latency_ms=0),
        Registry(),  # type: ignore[arg-type]
        Controls(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        Quotes(),
        publish,
        entry_thresholds={"balanced": Decimal(70)},
        market_refresher=Refresher(),
        ollama_policy=Model() if model_action else None,  # type: ignore[arg-type]
    )
    if model_action == "hold":
        engine._settings = engine._settings.model_copy(update={"execution_mode": "shadow"})

    await engine.monitor_open_positions()
    if failure == "no_rpc":
        recovery = next(item for item in published if isinstance(item, PaperOrderCompleted))
        assert recovery.result.fill is None
        assert recovery.result.rejection_reason == "execution_rpc_state_unavailable"
        assert observations == []
        await engine.monitor_open_positions()
    if failure == "no_quote":
        recovery = next(item for item in published if isinstance(item, PaperOrderCompleted))
        assert recovery.result.fill is None
        assert recovery.result.rejection_reason == "quote_price_unavailable"
        await engine.monitor_open_positions()

    order = next(
        item
        for item in published
        if isinstance(item, PaperOrderCompleted) and item.result.fill is not None
    )
    # Both detection and execution-time banks are retained.
    assert observations == [order.result.fill.actual_fill_price_raw] * 2
    assert order.result.status == PaperOrderStatus.FILLED
    assert order.result.exit_reason == "stop_loss"
    assert order.shadow_only is (model_action == "hold")
    trace = order.result.fill.exit_telemetry
    assert trace["RPC_refresh_started_at"] and trace["RPC_refresh_completed_at"]
    assert trace["exit_triggered_at"] and trace["paper_fill_at"]
    assert trace["RPC_ms"] >= 0 and trace["lock_wait_ms"] >= 0
    assert len(trace["RPC_reads"]) == 2
    assert order.result.fill.execution_diagnostics["stop_metric"] == (
        "NET_EXECUTABLE_REMAINING_COST_BASIS"
    )


@pytest.mark.asyncio
async def test_fresh_trade_retries_persistent_automatic_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine_module, "utc_now", lambda: NOW)
    portfolio = PortfolioSnapshot(UUID(int=10), "USDT", Decimal(1000), Decimal(1000), Decimal(0), 0)
    market = atomic_market(
        ExecutionMarketSnapshot(
            MINT,
            MARKET,
            LaunchVenue.PUMP_FUN,
            MarketLifecycle.BONDING_CURVE,
            NOW,
            100,
            Decimal("0.1"),
            WRAPPED_SOL_MINT,
            100_000_000_000,
            10_000_000_000,
            100_000_000_000,
            10_000_000_000,
            normalized_state=approved_state(),
            is_mayhem_mode=False,
            price_source="rpc_reserves",
            received_timestamp=NOW,
            feed_timestamp=NOW,
            data_quality="test",
            rpc_state="healthy",
            feed_timestamp_estimated=False,
            price_source_disagreement_pct=Decimal(0),
        )
    )
    decision = StrategyDecisionCreated(
        decision_price=Decimal("0.1"),
        price_evidence=approved_evidence(),
        event_id=UUID(int=11),
        provider="test",
        source_event_at=NOW - timedelta(seconds=2),
        mint=MINT,
        strategy_key="conservative",
        strategy_version_id=UUID(int=12),
        active_strategy=True,
        action=StrategyDecisionAction.ENTER_CANDIDATE,
        regime=StrategyRegime.EARLY_MOMENTUM,
        risk_event_id=UUID(int=13),
        score=ScoreResult(
            final_score=Decimal(85),
            component_completeness_percent=Decimal(100),
            components=(
                ScoreComponent(
                    name="momentum",
                    configured_weight=Decimal(100),
                    availability="available",
                    score=Decimal(85),
                    component_status="COMPLETE",
                ),
            ),
        ),
        reasons=("test",),
    )
    pending_entry = PendingPaperAction(
        UUID(int=14),
        portfolio.portfolio_id,
        MINT,
        "automatic_entry",
        NOW + timedelta(seconds=20),
        decision,
        None,
    )
    finished: list[dict[str, object]] = []

    class Registry:
        async def active_paper_portfolio(self) -> PortfolioSnapshot:
            return portfolio

        async def open_position(self, mint: str) -> None:
            return None

        async def alpha_filter_snapshot(self, mint: str) -> None:
            return None

        async def paper_market_context(
            self, mint: str, *, as_of: datetime
        ) -> ExecutionMarketSnapshot:
            return market

        async def feature_observed_at(self, event_id: UUID | None) -> None:
            return None

        async def paper_risk_snapshot(self, mint: str, *, as_of: datetime) -> PortfolioRiskSnapshot:
            return PortfolioRiskSnapshot(
                portfolio.portfolio_id,
                Decimal(1000),
                Decimal(0),
                Decimal(0),
                Decimal(0),
                0,
                None,
                None,
            )

    class Controls:
        async def get(self) -> TradingControlSnapshot:
            return TradingControlSnapshot(
                False,
                "conservative",
                Decimal(5),
                Decimal(10),
                10,
                Decimal(20),
                Decimal(50),
                Decimal(15),
                1800,
            )

        async def is_blacklisted(self, mint: str) -> bool:
            return False

    class Pending:
        async def pending_for_mint(self, mint: str, *, action: str) -> PendingPaperAction | None:
            return pending_entry if action == "automatic_entry" else None

        async def finish(self, action_id: UUID, **values: object) -> None:
            finished.append({"action_id": action_id, **values})

    class Quotes:
        async def quote_price(self, portfolio_currency: str) -> QuotePrice:
            return QuotePrice(
                quote_asset=WRAPPED_SOL_MINT,
                portfolio_currency=portfolio_currency,
                price=Decimal(100),
                provenance=ProviderProvenance(
                    provider="test", observed_at=NOW, confidence=DataConfidence.HIGH
                ),
            )

        async def close(self) -> None:
            return None

    published: list[DomainEvent] = []

    async def publish(event: DomainEvent) -> int:
        published.append(event)
        return 1

    engine = PaperTradingEngine(
        Settings(
            _env_file=None,
            paper_compute_latency_ms=0,
            paper_submission_latency_ms=0,
            paper_max_entry_price_impact_bps_conservative=Decimal(2000),
            paper_entry_max_source_disagreement_percent=Decimal(5),
            paper_max_round_trip_cost_bps_conservative=Decimal(10000),
        ),
        Registry(),  # type: ignore[arg-type]
        Controls(),  # type: ignore[arg-type]
        Pending(),  # type: ignore[arg-type]
        Quotes(),
        publish,
        entry_thresholds={"conservative": Decimal(80)},
    )
    trade = TokenTrade(
        event_id=UUID(int=15),
        provider="test",
        source_event_at=NOW,
        mint=MINT,
        signature="b" * 64,
        side=TradeSide.BUY,
        token_amount=Decimal(100),
        quote_amount=Decimal(10),
        amounts_are_raw=True,
        quote_asset=WRAPPED_SOL_MINT,
        market=MARKET,
    )

    await engine.on_trade(trade)

    order = next(item for item in published if isinstance(item, PaperOrderCompleted))
    assert order.result.status == PaperOrderStatus.FILLED
    assert order.decision_event_id == decision.event_id
    assert finished[0]["status"] == "completed"
