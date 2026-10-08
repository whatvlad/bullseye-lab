from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from memebot.core.config import Settings
from memebot.paper.market_refresh import FallbackMarketSnapshotRefresher
from memebot.paper.price_safety import entry_data_block, price_metadata, source_disagreement
from memebot.paper.risk_governor import PortfolioRiskGovernor
from memebot.paper.validation_gate import require_price_validation
from test_paper_execution import NOW, _market, _policy, _quote
from test_portfolio_risk_governor import _state


def fresh_market():
    return replace(
        _market(),
        observed_at=NOW,
        price_source="rpc_reserves",
        received_timestamp=NOW,
        source_timestamp=None,
        feed_timestamp=NOW,
        data_quality="rpc_slot_known",
        rpc_state="healthy",
        feed_timestamp_estimated=False,
        price_source_disagreement_pct=Decimal(0),
    )


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"feed_timestamp": None}, "feed_timestamp_unknown_or_future"),
        ({"feed_timestamp": NOW - timedelta(seconds=6)}, "entry_feed_stale"),
        ({"feed_timestamp": NOW + timedelta(seconds=1)}, "feed_timestamp_unknown_or_future"),
        ({"feed_timestamp_estimated": True}, "entry_feed_source_time_unknown"),
        ({"rpc_state": "degraded"}, "entry_rpc_degraded"),
        ({"price_source": "unknown"}, "price_provenance_unknown"),
        ({"price_source_disagreement_pct": Decimal(73)}, "entry_price_sources_disagree"),
        ({"real_quote_reserves_raw": None}, "entry_executable_quote_incomplete"),
    ],
)
def test_entry_blocks_unknown_stale_degraded_and_incomplete_evidence(updates, reason):
    settings = Settings(_env_file=None, paper_entry_max_source_disagreement_percent=Decimal(5))
    assert entry_data_block(replace(fresh_market(), **updates), NOW, settings) == reason


def test_rpc_refresh_age_does_not_make_feed_fresh():
    market = replace(fresh_market(), feed_timestamp=NOW - timedelta(minutes=5))
    evidence = price_metadata(market, NOW)
    assert evidence["price_age_ms"] is None
    assert evidence["received_age_ms"] == 0
    assert evidence["feed_age_ms"] == 300000
    assert evidence["source_timestamp"] is None
    assert source_disagreement(None, Decimal(1)) is None


def test_no_invented_disagreement_threshold_or_unknown_comparison_allows_entry():
    assert entry_data_block(fresh_market(), NOW, Settings(_env_file=None)) == (
        "entry_disagreement_limit_unconfigured"
    )
    market = replace(fresh_market(), price_source_disagreement_pct=None)
    settings = Settings(_env_file=None, paper_entry_max_source_disagreement_percent=Decimal(5))
    assert entry_data_block(market, NOW, settings) == "entry_source_comparison_unavailable"


@pytest.mark.asyncio
async def test_fallback_continues_after_primary_timeout_and_preserves_old_feed_time():
    market = replace(fresh_market(), observed_at=NOW - timedelta(minutes=5))
    primary = AsyncMock()
    primary.refresh.side_effect = TimeoutError()
    secondary = AsyncMock()
    recovered = replace(market, observed_at=NOW, received_timestamp=NOW)
    secondary.refresh.return_value = recovered
    result = await FallbackMarketSnapshotRefresher(primary, secondary).refresh(market)
    assert result == recovered
    secondary.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_rpc_fallback_retains_reference_without_claiming_an_exit_fill():
    market = replace(fresh_market(), price_source="stream_reserves")
    rpc = AsyncMock()
    rpc.refresh.return_value = market
    result = await FallbackMarketSnapshotRefresher(rpc).refresh(market)
    assert result.observed_at == market.observed_at
    assert entry_data_block(result, NOW, Settings(_env_file=None)) == "entry_rpc_degraded"
    from memebot.models.paper import PositionEffect
    from memebot.paper.execution import PaperFillSimulator

    order = PaperFillSimulator(_policy()).simulate_sell(
        result,
        _quote(),
        token_amount_raw=Decimal(1000000),
        position_effect=PositionEffect.CLOSE,
        exit_reason="stop_loss",
        signal_at=NOW,
        decision_at=NOW,
    )
    assert order.fill is None
    assert order.rejection_reason == "execution_rpc_state_unavailable"


@pytest.mark.asyncio
async def test_unknown_or_old_position_execution_marks_block_new_exposure():
    registry = AsyncMock()
    registry.paper_risk_snapshot.return_value = _state(execution_marks_valid=False)
    result = await PortfolioRiskGovernor(Settings(_env_file=None), registry).assess_entry(
        "test",
        Decimal(1),
        as_of=NOW,
    )
    assert not result.allowed
    assert result.rejection_reason == "open_position_execution_marks_unavailable"


def test_runner_gate_blocks_missing_validation(tmp_path):
    with pytest.raises(ValueError, match="runner price validation blocked"):
        require_price_validation("runner-edge-prospective-v1", {}, root=tmp_path)


@pytest.mark.asyncio
async def test_terminal_curve_evidence_survives_failed_fallback():
    market = fresh_market()
    primary = AsyncMock()
    primary.refresh.return_value = replace(market, curve_complete=True)
    secondary = AsyncMock()
    secondary.refresh.return_value = market
    result = await FallbackMarketSnapshotRefresher(primary, secondary).refresh(market)
    assert result.curve_complete
    assert result.rpc_state == "degraded"


def test_paper_prices_are_quantity_specific_and_fee_evidence_is_consistent():
    from memebot.models.paper import PositionEffect
    from memebot.paper.execution import PaperFillSimulator

    market = replace(fresh_market(), decision_price=Decimal("0.12"))
    order = PaperFillSimulator(_policy()).simulate_sell(
        market,
        _quote(),
        token_amount_raw=Decimal(1_000_000_000),
        position_effect=PositionEffect.CLOSE,
        exit_reason="stop_loss",
        signal_at=NOW,
        decision_at=NOW,
    )
    fill = order.fill
    assert fill is not None
    assert fill.decision_price == Decimal("0.12")
    assert fill.reference_price == Decimal("0.1")
    assert fill.executable_quote < fill.reference_price
    assert fill.simulated_fill < fill.executable_quote
    assert fill.expected_fill_price_raw == fill.executable_quote
    assert fill.fees == fill.total_fee_portfolio
    assert fill.price_model_version == 2


def test_completed_order_metadata_uses_fill_snapshot_not_older_manual_context():
    from memebot.models.paper import PositionEffect
    from memebot.paper.execution import PaperFillSimulator
    from memebot.paper.price_safety import with_price_evidence

    current = fresh_market()
    result = PaperFillSimulator(_policy()).simulate_sell(
        current,
        _quote(),
        token_amount_raw=Decimal(1_000_000),
        position_effect=PositionEffect.CLOSE,
        exit_reason="manual_paper_sell",
        signal_at=NOW,
        decision_at=NOW,
    )
    older = replace(current, price_source="old_reference")
    result = with_price_evidence(result, older, NOW)
    assert result.price_evidence["price_source"] == "rpc_reserves"
