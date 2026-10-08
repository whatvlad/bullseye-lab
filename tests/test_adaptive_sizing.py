from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from memebot.core.config import Settings
from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import PaperOrderStatus
from memebot.paper.engine import PaperTradingEngine
from memebot.paper.models import ExecutionMarketSnapshot, PortfolioSnapshot
from memebot.providers.price.base import QuotePrice
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from memebot.storage.database.control import TradingControlSnapshot
from standard_evidence import approved_state, atomic_market

NOW = datetime(2026, 9, 13, tzinfo=UTC)
CONTROL = TradingControlSnapshot(
    False, "balanced", Decimal(30), Decimal(40), 5, Decimal(12), Decimal(100), Decimal(18), 1800
)
PORTFOLIO = PortfolioSnapshot(UUID(int=1), "USDT", Decimal(100), Decimal(100), Decimal(0), 0)


def engine() -> PaperTradingEngine:
    async def publish(event):
        return 1

    settings = Settings(
        _env_file=None,
        paper_adaptive_position_sizing=True,
        paper_risk_per_trade_percent=Decimal(12),
        paper_open_risk_budget_percent=Decimal(15),
    )
    return PaperTradingEngine(
        settings,
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
        publish,
        entry_thresholds={"balanced": Decimal(60)},
    )


def simulate(*, liquidity_sol: int, budget: Decimal = Decimal(40)):
    bot = engine()
    quote_reserve = liquidity_sol * 1_000_000_000
    market = atomic_market(
        ExecutionMarketSnapshot(
            "mint",
            "market",
            LaunchVenue.PUMP_FUN,
            MarketLifecycle.BONDING_CURVE,
            NOW,
            1,
            Decimal("0.1"),
            WRAPPED_SOL_MINT,
            quote_reserve * 10,
            quote_reserve,
            quote_reserve * 10,
            quote_reserve,
            normalized_state=approved_state(),
            is_mayhem_mode=False,
        )
    )
    quote = QuotePrice(
        quote_asset=WRAPPED_SOL_MINT,
        portfolio_currency="USDT",
        price=Decimal(100),
        provenance=ProviderProvenance(
            provider="test", observed_at=NOW, confidence=DataConfidence.HIGH
        ),
    )
    return bot, bot._liquidity_adjusted_buy(
        portfolio=PORTFOLIO,
        control=CONTROL,
        strategy_key="balanced",
        target=Decimal(40),
        market=market,
        quote_price=quote,
        signal_at=NOW,
        decision_at=NOW,
        available_budget=budget,
    )


def test_adaptive_target_can_reach_forty_percent_without_score_amplification() -> None:
    bot = engine()
    for score in (60, 70, 99):
        assert bot._position_size(PORTFOLIO, Decimal(score), "balanced", CONTROL) == 40


def test_deep_liquidity_uses_nearly_forty_percent_including_extra_fees() -> None:
    bot, (amount, result) = simulate(liquidity_sol=1000)
    assert result.status == PaperOrderStatus.FILLED
    assert Decimal(39) < amount < Decimal(40)
    assert bot._entry_cash_cost(result) <= 40


def test_shallow_liquidity_cannot_escape_pessimistic_round_trip_cost_floor() -> None:
    _, (amount, result) = simulate(liquidity_sol=20)
    assert result.status == PaperOrderStatus.REJECTED
    assert result.rejection_reason == "round_trip_cost_above_strategy_limit"
    assert amount == 10


@pytest.mark.parametrize("budget", [Decimal(9), Decimal(10)])
def test_no_dust_order_when_budget_cannot_cover_minimum_plus_fees(budget: Decimal) -> None:
    _, (_, result) = simulate(liquidity_sol=1000, budget=budget)
    assert result.status == PaperOrderStatus.REJECTED
    assert result.rejection_reason == "minimum_order_not_affordable_within_limits"


def test_bad_liquidity_rejects_instead_of_shrinking_below_ten() -> None:
    _, (amount, result) = simulate(liquidity_sol=1)
    assert result.status == PaperOrderStatus.REJECTED
    assert amount == 10
