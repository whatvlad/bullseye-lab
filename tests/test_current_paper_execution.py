import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from memebot.core.config import Settings
from memebot.eligibility import paper_candidate_rejection
from memebot.intelligence.risk.coordinator import RiskAssessmentCoordinator
from memebot.models.common import DataConfidence, ProviderProvenance
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.models.paper import PaperOrderStatus, PositionEffect
from memebot.paper.execution import ExecutionPolicy, PaperFillSimulator
from memebot.paper.market_refresh import CurrentPaperMarketRefresher
from memebot.paper.models import ExecutionMarketSnapshot
from memebot.paper.price_safety import entry_data_block
from memebot.paper.standard_math import buy_exact_input, sell_quote
from memebot.providers.price.base import QuotePrice
from memebot.providers.solana.pump_idl import PUMP_PROGRAM_ID, WRAPPED_SOL_MINT
from standard_evidence import approved_state
from test_candidate_proof import Rpc, fixture


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "healthy,verified,expected", [(True, True, 1), (False, True, 0), (True, False, 0)]
)
async def test_risk_refresh_precedes_and_preserves_canonical_identity_guard(
    healthy, verified, expected
):
    fresh, _ = await current_market()
    state = fresh.normalized_state.model_copy(update={"execution_identity_verified": verified})
    refreshed = replace(
        fresh, normalized_state=state, rpc_state="healthy" if healthy else "degraded"
    )
    calls = []

    class Registry:
        async def risk_context(self, mint):
            return SimpleNamespace(market=fresh.market)

        async def paper_market_context(self, mint, as_of):
            return replace(
                fresh,
                normalized_state=state.model_copy(update={"execution_identity_verified": False}),
            )

    class Refresher:
        async def refresh(self, market):
            return refreshed

    class Collector:
        async def collect(self, context):
            calls.append(context)
            raise RuntimeError("stop after reaching collector")

    coordinator = RiskAssessmentCoordinator(
        Registry(),
        Collector(),
        None,
        None,
        worker_count=1,
        queue_size=10,
        reassessment_interval_seconds=10,
        max_assessments_per_hour=0,
        max_assessments_per_day=0,
        market_refresher=Refresher(),
    )
    event = SimpleNamespace(mint=fresh.mint, source_event_at=datetime.now(UTC), event_id=uuid4())
    await coordinator.start()
    coordinator._queue.put_nowait(event)
    await asyncio.wait_for(coordinator._queue.join(), 2)
    await coordinator.close()
    assert len(calls) == expected


async def current_market():
    candidate, accounts, tx, _, _ = fixture()
    at = datetime.now(UTC)
    market = ExecutionMarketSnapshot(
        candidate.mint,
        candidate.quality_evidence.get("curve", ""),
        LaunchVenue.PUMP_FUN,
        MarketLifecycle.BONDING_CURVE,
        at,
        100,
        Decimal(1),
        WRAPPED_SOL_MINT,
        None,
        None,
        None,
        None,
        normalized_state=approved_state(),
        is_mayhem_mode=False,
    )
    from memebot.providers.solana.canonical import curve_address

    market = replace(market, market=curve_address(candidate.mint))
    rpc = Rpc(accounts, tx)
    fresh = await CurrentPaperMarketRefresher(rpc).refresh(market)
    return fresh, rpc


def simulator():
    return PaperFillSimulator(
        ExecutionPolicy(
            Decimal(125),
            Decimal(50),
            Decimal("0.00001"),
            Decimal("0.0001"),
            0,
            0,
            5,
            180,
            require_atomic_pump_state=True,
        )
    )


def quote(at):
    return QuotePrice(
        quote_asset=WRAPPED_SOL_MINT,
        portfolio_currency="USD",
        price=Decimal(100),
        provenance=ProviderProvenance(
            provider="test", observed_at=at, confidence=DataConfidence.HIGH
        ),
    )


@pytest.mark.asyncio
async def test_one_atomic_bank_verifies_identity_and_current_config_without_history():
    fresh, rpc = await current_market()
    assert fresh.execution_state is not None
    assert fresh.rpc_state == "healthy"
    assert [method for method, _ in rpc.calls] == ["getMultipleAccounts"]
    assert entry_data_block(fresh, datetime.now(UTC), Settings(_env_file=None)) is None


@pytest.mark.asyncio
async def test_exact_dynamic_fees_and_pessimistic_buy_and_sell():
    fresh, _ = await current_market()
    at = datetime.now(UTC)
    state = fresh.execution_state
    assert state is not None
    expected = buy_exact_input(state["curve"], 50_000_000, state["rates"])
    result = simulator().simulate_buy(
        fresh,
        quote(at),
        requested_portfolio_amount=Decimal(5),
        signal_at=at,
        decision_at=at,
        executed_at=at,
    )
    assert result.fill is not None
    assert result.fill.token_amount_raw < expected["token_output"]
    assert result.fill.venue_fee_quote_raw == expected["protocol_fee"] + expected["creator_fee"]
    evidence = {e.code: e.value for e in result.fill.evidence}
    assert evidence["adverse_fill_bps"] == 50 and evidence["additional_slippage_bps"] == 50
    expected_sell = sell_quote(state["curve"], int(result.fill.token_amount_raw), state["rates"])
    sold = simulator().simulate_sell(
        fresh,
        quote(at),
        token_amount_raw=result.fill.token_amount_raw,
        position_effect=PositionEffect.CLOSE,
        exit_reason="test",
        signal_at=at,
        decision_at=at,
        executed_at=at,
    )
    assert sold.fill is not None
    assert sold.fill.gross_quote_amount_raw < expected_sell["gross_output"]
    assert (
        sold.fill.venue_fee_quote_raw
        == expected_sell["protocol_fee"] + expected_sell["creator_fee"]
    )


@pytest.mark.asyncio
async def test_missing_or_stale_atomic_state_never_fills_even_with_fresh_feed():
    fresh, _ = await current_market()
    at = datetime.now(UTC)
    for market in [
        replace(fresh, execution_state=None),
        replace(fresh, observed_at=at - timedelta(seconds=6)),
    ]:
        result = simulator().simulate_buy(
            market,
            quote(at),
            requested_portfolio_amount=Decimal(5),
            signal_at=at,
            decision_at=at,
            executed_at=at,
        )
        assert result.status == PaperOrderStatus.REJECTED


@pytest.mark.asyncio
async def test_malformed_canonical_account_rejects_current_read():
    candidate, accounts, tx, _, _ = fixture()
    accounts[candidate.mint]["owner"] = PUMP_PROGRAM_ID
    fresh, _ = await current_market()
    result = await CurrentPaperMarketRefresher(Rpc(accounts, tx)).refresh(fresh)
    assert result.rpc_state == "degraded" and result.execution_state is None


def test_history_gap_is_diagnostic_but_explicit_router_ambiguity_is_excluded():
    evidence = approved_state().evidence()
    evidence.update(
        state_quality="INCOMPLETE", continuity_status="UNKNOWN", state_reason="INDEX_LAG"
    )
    assert paper_candidate_rejection(evidence) is None
    evidence["state_reason"] = "UNRESOLVED_ROUTER_ROUTE"
    assert paper_candidate_rejection(evidence) == "KNOWN_INCOMPATIBLE_OR_AMBIGUOUS_STATE"


def test_live_execution_mode_remains_impossible():
    with pytest.raises(ValueError):
        Settings(_env_file=None, execution_mode="live")
