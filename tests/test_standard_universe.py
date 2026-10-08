from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from memebot.core.config import Settings
from memebot.eligibility import entry_rejection
from memebot.intelligence.alpha_filter import AlphaFilterService
from memebot.intelligence.risk.coordinator import RiskAssessmentCoordinator
from memebot.models.market import LaunchVenue
from memebot.models.paper import PositionEffect
from memebot.paper.execution import PaperFillSimulator
from memebot.providers.solana.bootstrap import ReadOnlyConfigCache, bootstrap_curve
from memebot.providers.solana.pump_idl import PUMP_AMM_PROGRAM_ID
from memebot.research.standard_universe import StandardUniverseCollector
from standard_evidence import approved_evidence, approved_state
from test_alpha_filter import _decision
from test_paper_execution import NOW, _market, _policy, _quote


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"is_mayhem_mode": True}, "OUT_OF_SCOPE_MAYHEM"),
        ({"is_mayhem_mode": None}, "TOKEN_MODE_UNKNOWN"),
        ({"program": PUMP_AMM_PROGRAM_ID}, "OUT_OF_SCOPE_PUMPSWAP"),
        ({"migrated": True}, "MIGRATED_MARKET"),
        ({"multi_event_ambiguous": True}, "MULTI_EVENT_AMBIGUOUS"),
        ({"state_semantics": "UNKNOWN"}, "STATE_UNKNOWN"),
        ({"continuity_status": "DIVERGED"}, "CONTINUITY_DIVERGED"),
        ({"continuity_status": "UNKNOWN"}, "STATE_UNKNOWN"),
        ({"state_quality": "UNKNOWN"}, "STATE_UNKNOWN"),
        ({"execution_identity_verified": False}, "IDENTITY_INCOMPLETE"),
        ({"execution_config_verified": False}, "EXECUTION_STATE_INCOMPLETE"),
        ({"execution_assumptions_verified": False}, "EXECUTION_STATE_INCOMPLETE"),
    ],
)
def test_every_universe_rejection_is_explicit(updates, reason):
    assert entry_rejection({**approved_evidence(), **updates}) == reason


def test_standard_proof_passes_scope_but_empty_evidence_cannot():
    assert entry_rejection(approved_evidence()) is None
    assert entry_rejection({}) == "STATE_UNKNOWN"


@pytest.mark.asyncio
async def test_excluded_alpha_decision_consumes_no_api_or_database_work():
    registry = AsyncMock()
    rpc = AsyncMock()
    service = AlphaFilterService(Settings(_env_file=None), registry, rpc)
    decision = _decision().model_copy(
        update={"price_evidence": {**approved_evidence(), "is_mayhem_mode": True}}
    )
    assert await service.assess(decision) is None
    assert not registry.mock_calls and not rpc.mock_calls


def test_excluded_trade_does_not_consume_risk_queue_or_budget():
    from memebot.events.models import TokenTrade

    coordinator = RiskAssessmentCoordinator(
        None,
        None,
        None,
        None,
        worker_count=1,
        queue_size=1,
        reassessment_interval_seconds=1,
        max_assessments_per_hour=1,
        max_assessments_per_day=1,
    )
    event = TokenTrade.model_construct(
        mint="excluded",
        normalized_state=approved_state().model_copy(update={"is_mayhem_mode": True}),
    )
    assert coordinator.enqueue(event)
    assert coordinator._queue.empty() and not coordinator._assessment_times


def test_mayhem_and_migrated_buy_rejection_preserves_exit_model():
    simulator = PaperFillSimulator(_policy())
    market = replace(_market(), is_mayhem_mode=True)
    buy = simulator.simulate_buy(
        market, _quote(), requested_portfolio_amount=Decimal(10), signal_at=NOW, decision_at=NOW
    )
    assert buy.rejection_reason == "OUT_OF_SCOPE_MAYHEM"
    sell = simulator.simulate_sell(
        market,
        _quote(),
        token_amount_raw=Decimal(1000),
        position_effect=PositionEffect.CLOSE,
        exit_reason="safety",
        signal_at=NOW,
        decision_at=NOW,
    )
    assert sell.fill is not None
    swap = replace(market, venue=LaunchVenue.PUMP_SWAP, is_mayhem_mode=False)
    assert (
        simulator.simulate_buy(
            swap, _quote(), requested_portfolio_amount=Decimal(10), signal_at=NOW, decision_at=NOW
        ).rejection_reason
        == "OUT_OF_SCOPE_PUMPSWAP"
    )


@pytest.mark.asyncio
async def test_mayhem_bootstrap_is_excluded_before_identity_reads():
    from memebot.providers.solana.pump_idl import (
        NATIVE_SOL_MINT,
        PUMP_PROGRAM_ID,
        BondingCurveAccount,
    )
    from test_state_trust import CURVE, MINT, _account

    rpc = AsyncMock()
    curve = BondingCurveAccount(
        1000, 2000, 800, 100, 10000, False, MINT, True, False, NATIVE_SOL_MINT
    )
    proof = await bootstrap_curve(
        rpc,
        "confirmed",
        mint=MINT,
        account=_account(CURVE, PUMP_PROGRAM_ID, 10, b"unused"),
        curve=curve,
        config_version=None,
    )
    assert proof.identity is None and not proof.checks["standard_mode"]
    assert not rpc.mock_calls


@pytest.mark.asyncio
async def test_standard_config_cache_reads_only_pump_and_ignores_swap_churn():
    rpc = AsyncMock()
    rpc.get_multiple_accounts.return_value = [None, None]
    cache = ReadOnlyConfigCache(rpc, "confirmed")
    await cache.ensure({})
    assert len(rpc.get_multiple_accounts.call_args.args[0]) == 2
    assert set(cache.records) == {"pump_global", "pump_fee"}
    await cache.ensure({PUMP_AMM_PROGRAM_ID: 1})
    assert rpc.get_multiple_accounts.await_count == 1


@pytest.mark.asyncio
async def test_passive_standard_collector_has_no_rpc_budget_or_swap_subscription():
    collector = StandardUniverseCollector(Settings(_env_file=None))
    try:
        assert PUMP_AMM_PROGRAM_ID not in collector.native_programs
        assert collector.budget.limit == 0
    finally:
        for rpc in collector.rpcs:
            await rpc.close()
