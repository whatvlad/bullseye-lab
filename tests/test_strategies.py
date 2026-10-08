from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from memebot.events.models import MarketFeatureSnapshotCreated, TokenRiskAssessed
from memebot.intelligence.features.models import RollingWindowMetrics
from memebot.models.market import MarketLifecycle, MarketValidationState
from memebot.models.risk import RiskResult
from memebot.models.strategy import StrategyDecisionAction, StrategyRegime
from memebot.strategies.presets import initial_strategy_presets
from memebot.strategies.regimes import classify_regime
from memebot.strategies.runner import MultiStrategyRunner
from memebot.strategies.scoring import TransparentScoreEngine
from standard_evidence import approved_evidence

MINT = "So11111111111111111111111111111111111111112"
MARKET = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
NOW = datetime(2026, 8, 22, 23, 0, tzinfo=UTC)


def _metric(window: int, trades: int = 12) -> RollingWindowMetrics:
    return RollingWindowMetrics(
        window_seconds=window,
        trade_count=trades,
        buy_count=10,
        sell_count=2,
        unique_buyers=8,
        unique_sellers=2,
        buy_volume_quote_raw=Decimal(900),
        sell_volume_quote_raw=Decimal(100),
        total_volume_quote_raw=Decimal(1000),
        flow_imbalance=Decimal("0.8"),
        open_price_raw=Decimal(1),
        close_price_raw=Decimal(2),
        price_change_percent=Decimal(20),
        price_sample_count=trades,
        missing_price_sample_count=0,
        price_observation_span_seconds=Decimal(window),
        price_velocity_percent_per_second=Decimal(10),
        price_acceleration_percent_per_second2=Decimal(1),
        volume_velocity_quote_raw_per_second=Decimal(100),
        volume_acceleration_quote_raw_per_second2=Decimal(20),
        transaction_rate_per_second=Decimal(1),
        transaction_rate_acceleration_per_second2=Decimal("0.2"),
        unique_buyer_rate_acceleration_per_second2=Decimal("0.1"),
        buy_pressure_acceleration_per_second=Decimal("0.02"),
        observation_span_seconds=Decimal(window),
        buyer_wallet_attribution_percent=Decimal(100),
        largest_buyer_volume_share=Decimal("0.25"),
    )


def _feature() -> MarketFeatureSnapshotCreated:
    return MarketFeatureSnapshotCreated(
        event_id=UUID(int=301),
        provider="rolling_feature_engine",
        source_event_at=NOW,
        source_slot=800,
        mint=MINT,
        trigger_event_id=UUID(int=300),
        lifecycle=MarketLifecycle.BONDING_CURVE,
        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
        lifecycle_age_seconds=20,
        bonding_progress_percent=Decimal(20),
        market=MARKET,
        latest_price_raw=Decimal(2),
        windows=(_metric(10), _metric(30), _metric(60)),
        price_evidence=approved_evidence(),
    )


def _risk(*, allowed: bool | None = True) -> TokenRiskAssessed:
    hard = ("freeze_authority_enabled",) if allowed is False else ()
    return TokenRiskAssessed(
        event_id=UUID(int=302),
        provider="bullseye_risk_engine",
        source_event_at=NOW,
        source_slot=800,
        mint=MINT,
        trigger_event_id=UUID(int=299),
        market=MARKET,
        result=RiskResult(
            allowed=allowed,
            risk_score=Decimal(10) if allowed is True else None,
            data_completeness_percent=Decimal(90),
            hard_reject_reasons=hard,
            critical_unknowns=("holder_distribution",) if allowed is None else (),
        ),
    )


def test_regime_classifier_detects_early_momentum_without_future_data() -> None:
    assert (
        classify_regime(
            MarketLifecycle.BONDING_CURVE,
            token_age_seconds=45,
            momentum_score=Decimal(75),
        )
        == StrategyRegime.EARLY_MOMENTUM
    )
    assert (
        classify_regime(
            MarketLifecycle.BONDING_CURVE,
            token_age_seconds=300,
            momentum_score=Decimal(75),
        )
        == StrategyRegime.BONDING_CURVE
    )


def test_transparent_score_retains_components_and_unknown_wallet_data() -> None:
    aggressive = next(item for item in initial_strategy_presets() if item.key == "aggressive")
    scorer = TransparentScoreEngine()

    result = scorer.score(
        _feature(),
        _risk().result,
        aggressive,
        regime=StrategyRegime.EARLY_MOMENTUM,
    )

    assert result.final_score is not None
    assert result.component_completeness_percent == Decimal("70.00")
    components = {item.name: item for item in result.components}
    assert components["wallet"].score is None
    assert components["wallet"].reason == "wallet_alpha_research_only_until_phase_9"
    assert components["social"].reason == "social_weight_disabled"
    assert components["momentum"].evidence


def test_multi_strategy_replay_is_deterministic_and_aggressive_is_active() -> None:
    runner = MultiStrategyRunner(initial_strategy_presets())
    risk = _risk()

    first = runner.evaluate(risk, _feature(), token_created_at=NOW - timedelta(seconds=45))
    second = runner.evaluate(risk, _feature(), token_created_at=NOW - timedelta(seconds=45))

    assert [item.model_dump(mode="json") for item in first] == [
        item.model_dump(mode="json") for item in second
    ]
    assert len(first) == 3
    aggressive = next(item for item in first if item.strategy_key == "aggressive")
    assert aggressive.active_strategy is True
    assert aggressive.action == StrategyDecisionAction.ENTER_CANDIDATE


def test_aggressive_v10_accepts_early_distributed_buying_without_disabling_risk_gate() -> None:
    aggressive = next(item for item in initial_strategy_presets() if item.key == "aggressive")
    assert aggressive.version == 10
    assert aggressive.minimum_trades_in_window == 5
    assert aggressive.minimum_unique_buyers_in_window == 3
    assert aggressive.minimum_observation_seconds == 3
    metric = _metric(10, trades=5).model_copy(
        update={
            "buy_count": 4,
            "sell_count": 1,
            "unique_buyers": 3,
            "flow_imbalance": Decimal("0.15"),
            "observation_span_seconds": Decimal(3),
            "price_observation_span_seconds": Decimal(3),
            "buyer_wallet_attribution_percent": Decimal(72),
            "largest_buyer_volume_share": Decimal("0.62"),
            "price_change_percent": Decimal(12),
        }
    )
    feature = _feature().model_copy(update={"windows": (metric, _metric(30), _metric(60))})
    runner = MultiStrategyRunner(initial_strategy_presets())
    decisions = runner.evaluate(_risk(), feature, token_created_at=NOW - timedelta(seconds=5))
    candidate = next(item for item in decisions if item.strategy_key == "aggressive")
    assert candidate.action == StrategyDecisionAction.ENTER_CANDIDATE
    rejected = runner.evaluate(
        _risk(allowed=False), feature, token_created_at=NOW - timedelta(seconds=5)
    )
    assert (
        next(item for item in rejected if item.strategy_key == "aggressive").action
        == StrategyDecisionAction.SKIP
    )


def test_hard_reject_skips_every_strategy_regardless_of_score() -> None:
    decisions = MultiStrategyRunner(initial_strategy_presets()).evaluate(
        _risk(allowed=False),
        _feature(),
        token_created_at=NOW - timedelta(seconds=60),
    )

    assert all(item.action == StrategyDecisionAction.SKIP for item in decisions)
    assert all("risk_gate_not_approved" in item.reasons for item in decisions)


def test_runtime_active_strategy_override_is_reflected_in_decisions() -> None:
    decisions = MultiStrategyRunner(initial_strategy_presets()).evaluate(
        _risk(),
        _feature(),
        token_created_at=NOW - timedelta(seconds=60),
        active_strategy_key="balanced",
    )

    assert [item.strategy_key for item in decisions if item.active_strategy] == ["balanced"]


def test_all_strategies_include_graduation_velocity_research_component() -> None:
    feature = _feature().model_copy(
        update={
            "bonding_progress_percent": Decimal(80),
            "windows": tuple(
                metric.model_copy(
                    update={
                        "quote_reserve_velocity_raw_per_second": Decimal(90),
                        "buyer_volume_hhi": Decimal("0.15"),
                        "largest_buyer_volume_share": Decimal("0.25"),
                        "buyer_wallet_attribution_percent": Decimal(100),
                    }
                )
                for metric in _feature().windows
            ),
        }
    )
    decisions = MultiStrategyRunner(initial_strategy_presets()).evaluate(
        _risk(),
        feature,
        token_created_at=NOW - timedelta(seconds=45),
        active_strategy_key="balanced",
    )
    assert {item.strategy_key for item in decisions} == {
        "conservative",
        "balanced",
        "aggressive",
    }
    for decision in decisions:
        components = {item.name: item for item in decision.score.components}
        assert components["graduation_velocity"].score is not None
        assert components["graduation_velocity"].configured_weight == 30


def test_balanced_v9_uses_buyer_confirmation_and_anti_chase_limit() -> None:
    balanced = next(item for item in initial_strategy_presets() if item.key == "balanced")

    assert balanced.version == 9
    assert balanced.score_threshold == Decimal(60)
    assert balanced.minimum_trades_in_window == 10
    assert balanced.minimum_unique_buyers_in_window == 6
    assert balanced.maximum_price_change_percent == Decimal(35)
    assert balanced.minimum_token_age_seconds == 10
    assert balanced.minimum_observation_seconds == 15
    assert balanced.require_sell_absorption
    assert balanced.minimum_component_completeness_percent == Decimal(50)


def test_balanced_skips_price_extension_instead_of_chasing() -> None:
    feature = _feature().model_copy(
        update={
            "windows": tuple(
                metric.model_copy(update={"price_change_percent": Decimal(45)})
                if metric.window_seconds == 30
                else metric
                for metric in _feature().windows
            )
        }
    )

    decision = next(
        item
        for item in MultiStrategyRunner(initial_strategy_presets()).evaluate(
            _risk(),
            feature,
            token_created_at=NOW - timedelta(seconds=45),
            active_strategy_key="balanced",
        )
        if item.strategy_key == "balanced"
    )

    assert decision.action == StrategyDecisionAction.SKIP
    assert "price_extension_above_entry_limit" in decision.reasons
