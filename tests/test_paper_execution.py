from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import FillQuality, PaperOrderStatus, PositionEffect
from memebot.paper.execution import ExecutionPolicy, PaperFillSimulator
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.providers.price.base import QuotePrice
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT
from standard_evidence import approved_state

MINT = "So11111111111111111111111111111111111111112"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
NOW = datetime(2026, 8, 22, 23, 45, tzinfo=UTC)


def _policy(*, fee_bps: str = "100", stale: int = 5) -> ExecutionPolicy:
    return ExecutionPolicy(
        venue_fee_bps=Decimal(fee_bps),
        latency_slippage_bps=Decimal(50),
        network_fee_sol=Decimal("0.00001"),
        priority_fee_sol=Decimal("0.0001"),
        compute_latency_ms=50,
        submission_latency_ms=750,
        max_market_staleness_seconds=stale,
        max_quote_price_staleness_seconds=90,
    )


def _market(*, quote_reserve: int = 10_000_000_000) -> ExecutionMarketSnapshot:
    return ExecutionMarketSnapshot(
        mint=MINT,
        market=MARKET,
        venue=LaunchVenue.PUMP_FUN,
        lifecycle=MarketLifecycle.BONDING_CURVE,
        observed_at=NOW - timedelta(seconds=1),
        source_slot=1000,
        observed_price_raw=Decimal("0.1"),
        quote_asset=WRAPPED_SOL_MINT,
        real_token_reserves_raw=100_000_000_000,
        real_quote_reserves_raw=quote_reserve,
        virtual_token_reserves_raw=100_000_000_000,
        virtual_quote_reserves_raw=quote_reserve,
        normalized_state=approved_state(),
        is_mayhem_mode=False,
    )


def _quote() -> QuotePrice:
    return QuotePrice(
        quote_asset=WRAPPED_SOL_MINT,
        portfolio_currency="USDT",
        price=Decimal(100),
        provenance=ProviderProvenance(
            provider="test_quote",
            observed_at=NOW - timedelta(seconds=2),
            confidence=DataConfidence.HIGH,
        ),
    )


def test_buy_fill_records_latency_price_impact_fees_and_no_signal_price_fill() -> None:
    result = PaperFillSimulator(_policy()).simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(100),
        signal_at=NOW - timedelta(seconds=3),
        decision_at=NOW,
    )

    assert result.status == PaperOrderStatus.FILLED
    assert result.fill is not None
    assert result.fill.filled_at > result.fill.decision_at > result.fill.signal_at
    assert result.fill.actual_fill_price_raw > result.fill.observed_price_raw
    assert result.fill.price_impact_bps > 0
    assert result.fill.total_fee_portfolio > 0
    assert result.fill.simulated_latency_ms == 800
    assert result.fill.execution_provider_fee_quote_raw > 0
    evidence = {item.code: item.value for item in result.fill.evidence}
    assert evidence["execution_provider_fee_bps"] == Decimal(50)


def test_larger_order_has_more_price_impact() -> None:
    simulator = PaperFillSimulator(_policy())
    small = simulator.simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(10),
        signal_at=NOW,
        decision_at=NOW,
    )
    large = simulator.simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(500),
        signal_at=NOW,
        decision_at=NOW,
    )

    assert small.fill is not None and large.fill is not None
    assert large.fill.price_impact_bps > small.fill.price_impact_bps


def test_pump_buy_uses_fee_inclusive_integer_budget_quote() -> None:
    # Official buyExactSolIn: 1 SOL budget, 95+30 bps; net=987654320,
    # rounded fees=9382717+2962963, curve input=net-1.
    result = PaperFillSimulator(replace(_policy(), latency_slippage_bps=Decimal(0))).simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(100),
        signal_at=NOW,
        decision_at=NOW,
    )
    assert result.fill is not None
    assert result.fill.venue_fee_quote_raw == Decimal(12345680)
    assert result.fill.token_amount_raw == Decimal(8988764028)


def test_runtime_fill_cannot_precede_modeled_latency() -> None:
    import pytest

    simulator = PaperFillSimulator(_policy())
    with pytest.raises(ValueError, match="execution_precedes_submission"):
        simulator.simulate_buy(
            _market(),
            _quote(),
            requested_portfolio_amount=Decimal(10),
            signal_at=NOW,
            decision_at=NOW,
            executed_at=NOW + timedelta(milliseconds=799),
        )
    result = simulator.simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(10),
        signal_at=NOW,
        decision_at=NOW,
        executed_at=NOW + timedelta(milliseconds=800),
    )
    assert result.fill is not None
    assert result.fill.filled_at == NOW + timedelta(milliseconds=800)


def test_completed_curve_cannot_fill_even_with_virtual_liquidity() -> None:
    result = PaperFillSimulator(_policy()).simulate_buy(
        replace(_market(), curve_complete=True),
        _quote(),
        requested_portfolio_amount=Decimal(10),
        signal_at=NOW,
        decision_at=NOW,
    )
    assert result.status == PaperOrderStatus.REJECTED


def test_sell_does_not_spend_virtual_sol_as_real_liquidity() -> None:
    market = replace(_market(), real_quote_reserves_raw=1)
    result = PaperFillSimulator(_policy()).simulate_sell(
        market,
        _quote(),
        token_amount_raw=Decimal(1000000),
        position_effect=PositionEffect.CLOSE,
        exit_reason="test",
        signal_at=NOW,
        decision_at=NOW,
    )
    assert result.status == PaperOrderStatus.REJECTED


def test_missing_reserves_stale_data_and_fee_consumed_order_are_rejected() -> None:
    missing = replace(
        _market(),
        real_token_reserves_raw=None,
        real_quote_reserves_raw=None,
        virtual_token_reserves_raw=None,
        virtual_quote_reserves_raw=None,
    )
    missing_result = PaperFillSimulator(_policy()).simulate_buy(
        missing,
        _quote(),
        requested_portfolio_amount=Decimal(100),
        signal_at=NOW,
        decision_at=NOW,
    )
    stale_market = _market()
    stale_result = PaperFillSimulator(_policy(stale=1)).simulate_buy(
        stale_market,
        _quote(),
        requested_portfolio_amount=Decimal(100),
        signal_at=NOW,
        decision_at=NOW + timedelta(seconds=2),
    )
    fee_result = PaperFillSimulator(_policy(fee_bps="10000")).simulate_buy(
        replace(_market(), venue=LaunchVenue.OTHER),
        _quote(),
        requested_portfolio_amount=Decimal(100),
        signal_at=NOW,
        decision_at=NOW,
    )

    assert missing_result.rejection_reason == "reliable_market_reserves_unavailable"
    assert stale_result.rejection_reason == "market_snapshot_stale"
    assert fee_result.rejection_reason == "OUT_OF_SCOPE_VENUE"


def test_pump_fee_estimate_does_not_admit_pumpswap() -> None:
    simulator = PaperFillSimulator(_policy(fee_bps="99"))
    bonding = simulator.simulate_buy(
        _market(),
        _quote(),
        requested_portfolio_amount=Decimal(10),
        signal_at=NOW,
        decision_at=NOW,
    )
    pumpswap = simulator.simulate_buy(
        replace(
            _market(),
            venue=LaunchVenue.PUMP_SWAP,
            lifecycle=MarketLifecycle.POST_GRADUATION,
            observed_price_raw=Decimal("0.0005"),
        ),
        _quote(),
        requested_portfolio_amount=Decimal(10),
        signal_at=NOW,
        decision_at=NOW,
    )

    assert bonding.fill is not None
    assert pumpswap.fill is None
    assert pumpswap.rejection_reason == "OUT_OF_SCOPE_PUMPSWAP"
    bonding_evidence = {item.code: item.value for item in bonding.fill.evidence}
    assert bonding_evidence["effective_venue_fee_bps"] == Decimal(125)


def test_partial_sell_has_partial_close_effect_and_exit_reason() -> None:
    simulator = PaperFillSimulator(_policy())
    result = simulator.simulate_sell(
        _market(),
        _quote(),
        token_amount_raw=Decimal(1_000_000),
        position_effect=PositionEffect.PARTIAL_CLOSE,
        exit_reason="partial_take_profit",
        signal_at=NOW,
        decision_at=NOW,
    )

    assert result.status == PaperOrderStatus.FILLED
    assert result.position_effect == PositionEffect.PARTIAL_CLOSE
    assert result.exit_reason == "partial_take_profit"


def test_operator_can_force_degraded_paper_close_from_stale_snapshot() -> None:
    stale_market = replace(_market(), observed_at=NOW - timedelta(seconds=45))
    result = PaperFillSimulator(_policy()).simulate_sell(
        stale_market,
        _quote(),
        token_amount_raw=Decimal(1_000_000),
        position_effect=PositionEffect.CLOSE,
        exit_reason="manual_paper_force_sell",
        signal_at=stale_market.observed_at,
        decision_at=NOW,
        allow_stale_market=True,
    )

    assert result.status == PaperOrderStatus.FILLED
    assert result.fill is not None
    assert result.fill.fill_quality == FillQuality.DEGRADED
    evidence = {item.code: item.value for item in result.fill.evidence}
    assert evidence["forced_stale_market_age_seconds"] == 45


def test_partial_sell_uses_integer_raw_units_and_zero_quantity_rejects() -> None:
    simulator = PaperFillSimulator(_policy())
    result = simulator.simulate_sell(
        _market(),
        _quote(),
        token_amount_raw=Decimal("1000000.75"),
        position_effect=PositionEffect.PARTIAL_CLOSE,
        exit_reason="test",
        signal_at=NOW,
        decision_at=NOW,
    )
    assert result.fill is not None
    assert result.fill.token_amount_raw == Decimal(1000000)
    zero = simulator.simulate_sell(
        _market(),
        _quote(),
        token_amount_raw=Decimal("0.5"),
        position_effect=PositionEffect.PARTIAL_CLOSE,
        exit_reason="test",
        signal_at=NOW,
        decision_at=NOW,
    )
    assert zero.rejection_reason == "non_positive_fill"
