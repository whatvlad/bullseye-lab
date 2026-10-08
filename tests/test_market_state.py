from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from memebot.market_state import (
    MarketIdentity,
    MarketStateTracker,
    NormalizedMarketState,
    ReconciliationPolicy,
    ReserveSemantics,
    StateStatus,
    normalize_trade,
)
from memebot.providers.solana.pump import unsupported_native_mutation
from memebot.providers.solana.pump_idl import PUMP_AMM_PROGRAM_ID, PumpSwapTrade, PumpTrade

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def swap(**kwargs):
    return replace(PumpSwapTrade(1, "pool", "user", True, 100, 55, 1000, 500, 20, 50), **kwargs)


def observe(tracker, event, slot=1, signature="a", ordinal=0):
    return tracker.observe(event, market="pool", slot=slot, signature=signature, ordinal=ordinal)


def identity(**kwargs):
    return replace(
        MarketIdentity(
            "pump_swap",
            PUMP_AMM_PROGRAM_ID,
            "pool",
            "mint",
            "quote",
            "base_vault",
            "quote_vault",
            None,
            True,
            20,
            0,
            "config-v1",
            True,
            config_verified=True,
            execution_assumptions_verified=True,
        ),
        **kwargs,
    )


def test_pumpswap_buy_uses_actual_transfer_preserves_pre():
    state = normalize_trade(swap(), market="pool", slot=1, signature="a", ordinal=0)
    assert state.reserve_semantics == ReserveSemantics.RECONSTRUCTED_POST_TRADE
    assert (state.raw_pre_token, state.raw_pre_quote) == (1000, 500)
    assert (state.token_reserve, state.quote_reserve) == (900, 550)
    assert state.observational_price == Decimal(570) / 900
    assert state.state_quality == StateStatus.INCOMPLETE


def test_pumpswap_sell_and_missing_transfer():
    state = normalize_trade(swap(is_buy=False), market="pool", slot=1, signature="a", ordinal=0)
    assert (state.token_reserve, state.quote_reserve) == (1100, 450)
    state = normalize_trade(
        swap(quote_vault_transfer=None), market="pool", slot=1, signature="a", ordinal=0
    )
    assert state.reserve_semantics == ReserveSemantics.UNKNOWN
    assert state.observational_price is None


def test_pumpfun_post_and_multi_event_unknown():
    event = PumpTrade("mint", 50, 100, True, "user", 1, 900, 650, 800, 550, "quote")
    state = normalize_trade(event, market="pool", slot=1, signature="a", ordinal=0)
    assert state.reserve_semantics == ReserveSemantics.POST_TRADE
    assert state.observational_price == Decimal(650) / 900
    state = normalize_trade(
        event, market="pool", slot=1, signature="a", ordinal=0, multi_event_unknown=True
    )
    assert state.reserve_semantics == ReserveSemantics.UNKNOWN
    assert state.quote_reserve is None


def _pump(**kwargs):
    return replace(
        PumpTrade("mint", 50, 100, True, "user", 1, 900, 650, 800, 550, "quote"), **kwargs
    )


def test_pumpfun_trade_reanchors_after_invalidation_from_another_transaction():
    tracker = MarketStateTracker()
    observe(tracker, _pump())
    tracker.invalidate("pool", "UNKNOWN_NATIVE_INSTRUCTION", signature="other")
    state = observe(tracker, _pump(virtual_token_reserves=850), slot=2, signature="next")
    assert state.continuity_status == "FIRST_OBSERVATION"
    assert state.reason == "reanchored_on_native_trade_event"
    assert state.invalidation_reason is None
    assert state.observational_price == Decimal(650) / 850
    # Execution trust is not restored by an observation.
    assert state.state_quality == StateStatus.INCOMPLETE
    assert not state.execution_identity_verified


def test_pumpfun_trade_does_not_reanchor_on_its_own_uncertain_transaction():
    tracker = MarketStateTracker()
    observe(tracker, _pump())
    tracker.invalidate("pool", "UNKNOWN_NATIVE_INSTRUCTION", signature="same")
    chained = _pump(
        virtual_quote_reserves=700,
        virtual_token_reserves=800,
        real_quote_reserves=600,
        real_token_reserves=700,
    )
    state = observe(tracker, chained, slot=2, signature="same")
    assert state.continuity_status == "UNKNOWN"
    assert state.observational_price is None
    state = tracker.observe(
        _pump(), market="pool", slot=3, signature="later", ordinal=0, multi_event_unknown=True
    )
    assert state.continuity_status == "UNKNOWN"


def test_exact_same_transaction_order_and_missing_mutation_diverge():
    tracker = MarketStateTracker()
    observe(tracker, swap())
    state = observe(
        tracker, swap(pool_base_token_reserves=900, pool_quote_token_reserves=550), ordinal=1
    )
    assert state.continuity_status == "EXACT"
    state = observe(
        tracker,
        swap(pool_base_token_reserves=750, pool_quote_token_reserves=650),
        slot=2,
        signature="b",
    )
    assert state.state_quality == StateStatus.DIVERGED
    assert state.delta == {"quote": 50, "token": -50}
    assert state.observational_price is None
    # A later internally consistent tick cannot erase the lost history.
    state = observe(
        tracker,
        swap(pool_base_token_reserves=650, pool_quote_token_reserves=700),
        slot=3,
        signature="c",
    )
    assert state.continuity_status == "UNKNOWN"
    assert state.observational_price is None


def test_older_slot_cannot_overwrite_and_rpc_recovers():
    tracker = MarketStateTracker()
    state = observe(tracker, swap(), slot=20)
    assert tracker.reconcile(identity(), state, validated=True, now=NOW)
    healthy = tracker.states["pool"]
    assert healthy.state_quality == StateStatus.HEALTHY
    rejected = observe(tracker, swap(), slot=19, signature="b")
    assert rejected.continuity_status == "SLOT_REGRESSION"
    assert tracker.states["pool"] == healthy
    tracker.invalidate("pool", "direct_vault_change")
    assert tracker.states["pool"].state_quality == StateStatus.INCOMPLETE
    assert tracker.reconcile(identity(), state, validated=True, now=NOW)
    assert tracker.states["pool"].continuity_status == "RPC_VALIDATED"


@pytest.mark.parametrize(
    "change", [{"base_mint": "wrong"}, {"config_version": "v2"}, {"quote_vault": "wrong"}]
)
def test_identity_and_config_mismatch_require_rebootstrap(change):
    tracker = MarketStateTracker()
    state = observe(tracker, swap())
    assert tracker.reconcile(identity(), state, validated=True, now=NOW)
    assert not tracker.reconcile(identity(**change), state, validated=True, now=NOW)
    assert tracker.states["pool"].state_quality == StateStatus.INCOMPLETE
    assert "pool" not in tracker.identities


def test_incomplete_identity_cannot_become_healthy():
    tracker = MarketStateTracker()
    state = observe(tracker, swap())
    assert tracker.reconcile(
        identity(config_version=None, canonical_verified=False), state, validated=True, now=NOW
    )
    assert tracker.states["pool"].state_quality == StateStatus.INCOMPLETE


def test_mutation_detector_respects_token_program_scope():
    logs = [
        f"Program {PUMP_AMM_PROGRAM_ID} invoke [1]",
        "Program log: Instruction: Buy",
        "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke [2]",
        "Program log: Instruction: TransferChecked",
        "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA success",
        f"Program {PUMP_AMM_PROGRAM_ID} success",
    ]
    assert unsupported_native_mutation(logs) is None
    logs[1] = "Program log: Instruction: Deposit"
    assert unsupported_native_mutation(logs) == "unsupported_native_instruction"
    assert unsupported_native_mutation(["Log truncated"]) == "native_logs_truncated"


def test_policy_entry_exit_always_refresh_and_no_fixed_polling_default():
    policy = ReconciliationPolicy()
    state = NormalizedMarketState()
    assert not policy.due(state, NOW, "periodic")
    assert not policy.due(state, NOW, "event_count")
    assert policy.due(state, NOW, "pre_entry")
    assert policy.due(state, NOW, "exit")
    assert policy.due(state, NOW, "divergence")


def test_strategy_rejects_unknown_state():
    from datetime import timedelta

    from memebot.strategies.presets import initial_strategy_presets
    from memebot.strategies.runner import MultiStrategyRunner
    from test_strategies import NOW as STRATEGY_NOW
    from test_strategies import _feature, _risk

    feature = _feature().model_copy(update={"price_evidence": {"state_quality": "UNKNOWN"}})
    decisions = MultiStrategyRunner(initial_strategy_presets()).evaluate(
        _risk(), feature, token_created_at=STRATEGY_NOW - timedelta(seconds=5)
    )
    assert all(d.action.value == "skip" for d in decisions)
    assert all("STATE_UNKNOWN" in d.reasons for d in decisions)


def test_invalid_observation_does_not_disable_emergency_sell():
    from memebot.core.config import Settings
    from memebot.models.paper import PositionEffect
    from memebot.paper.execution import PaperFillSimulator
    from memebot.paper.price_safety import entry_data_block
    from test_price_safety import NOW as PRICE_NOW
    from test_price_safety import _policy, _quote, fresh_market

    market = replace(
        fresh_market(),
        normalized_state=NormalizedMarketState(
            state_source="validated_rpc",
            state_quality=StateStatus.INCOMPLETE,
            reserve_semantics=ReserveSemantics.POST_TRADE,
            continuity_status="RPC_VALIDATED",
            reason="observational_history_incomplete",
        ),
    )
    assert entry_data_block(market, PRICE_NOW, Settings(_env_file=None)) == "STATE_UNKNOWN"
    result = PaperFillSimulator(_policy()).simulate_sell(
        market,
        _quote(),
        token_amount_raw=Decimal(1_000_000),
        position_effect=PositionEffect.CLOSE,
        exit_reason="stop_loss",
        signal_at=PRICE_NOW,
        decision_at=PRICE_NOW,
    )
    assert result.fill is not None
    assert result.fill.state_quality == "INCOMPLETE"
    assert result.fill.continuity_status == "RPC_VALIDATED"
    # Observational failure is recoverable; rejected RPC evidence cannot be a fill.
    rejected = PaperFillSimulator(_policy()).simulate_sell(
        replace(market, rpc_state="degraded"),
        _quote(),
        token_amount_raw=Decimal(1_000_000),
        position_effect=PositionEffect.CLOSE,
        exit_reason="stop_loss",
        signal_at=PRICE_NOW,
        decision_at=PRICE_NOW,
    )
    assert rejected.fill is None
    assert rejected.rejection_reason == "execution_rpc_state_unavailable"
