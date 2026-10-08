from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid5

from memebot.eligibility import paper_candidate_rejection
from memebot.events.models import (
    MarketFeatureSnapshotCreated,
    StrategyDecisionCreated,
    TokenRiskAssessed,
)
from memebot.models.market import MarketLifecycle
from memebot.models.strategy import (
    StrategyConfiguration,
    StrategyDecisionAction,
)

from .price_signal import missing_price_inputs
from .regimes import classify_regime
from .scoring import TransparentScoreEngine

_DECISION_NAMESPACE = UUID("2ef74ef7-cf6c-5e0e-afb1-04266289657b")


class MultiStrategyRunner:
    def __init__(
        self,
        configurations: tuple[StrategyConfiguration, ...],
        scorer: TransparentScoreEngine | None = None,
    ) -> None:
        self._configurations = tuple(item for item in configurations if item.enabled)
        self._scorer = scorer or TransparentScoreEngine()

    def evaluate(
        self,
        risk_event: TokenRiskAssessed,
        feature: MarketFeatureSnapshotCreated | None,
        *,
        token_created_at: datetime | None,
        active_strategy_key: str | None = None,
    ) -> tuple[StrategyDecisionCreated, ...]:
        token_age = (
            max(0, int((risk_event.source_event_at - token_created_at).total_seconds()))
            if token_created_at is not None
            else None
        )
        decisions = []
        for configuration in self._configurations:
            momentum = self._scorer.momentum_score(feature, configuration.scoring_window_seconds)
            regime = classify_regime(
                feature.lifecycle if feature is not None else MarketLifecycle.UNKNOWN,
                token_age_seconds=token_age,
                momentum_score=momentum,
            )
            score = self._scorer.score(feature, risk_event.result, configuration, regime=regime)
            action, reasons = _decide(
                configuration,
                risk_event,
                feature,
                token_age,
                regime,
                score.final_score,
                score.component_completeness_percent,
            )
            decisions.append(
                StrategyDecisionCreated(
                    event_id=uuid5(
                        _DECISION_NAMESPACE,
                        f"{risk_event.event_id}:{configuration.version_id}",
                    ),
                    provider="bullseye_strategy_runner",
                    source_event_at=risk_event.source_event_at,
                    provider_received_at=risk_event.provider_received_at,
                    ingested_at=risk_event.ingested_at,
                    correlation_id=risk_event.correlation_id or risk_event.event_id,
                    source_slot=risk_event.source_slot,
                    mint=risk_event.mint,
                    strategy_key=configuration.key,
                    strategy_version_id=configuration.version_id,
                    active_strategy=(
                        configuration.key == active_strategy_key
                        if active_strategy_key is not None
                        else configuration.active_for_execution
                    ),
                    action=action,
                    regime=regime,
                    risk_event_id=risk_event.event_id,
                    feature_event_id=feature.event_id if feature is not None else None,
                    score=score,
                    reasons=reasons,
                    decision_price=feature.latest_price_raw if feature is not None else None,
                    price_evidence=feature.price_evidence if feature is not None else {},
                )
            )
        return tuple(decisions)


def _decide(
    configuration: StrategyConfiguration,
    risk_event: TokenRiskAssessed,
    feature: MarketFeatureSnapshotCreated | None,
    token_age: int | None,
    regime: object,
    final_score: Decimal | None,
    completeness: Decimal,
) -> tuple[StrategyDecisionAction, tuple[str, ...]]:
    reasons: list[str] = []
    missing = missing_price_inputs(
        feature,
        configuration.scoring_window_seconds,
        Decimal(configuration.minimum_observation_seconds),
    )
    if missing:
        reasons.append(
            "UNKNOWN_REQUIRED_PRICE_CHANGE"
            if "rolling_price_change" in missing
            else "REQUIRED_PRICE_SIGNAL_INCOMPLETE"
        )
        reasons.extend(f"missing_required_input:{item}" for item in missing)
    risk = risk_event.result
    if risk.allowed is not True:
        reasons.append("risk_gate_not_approved")
    if risk.hard_reject_reasons:
        reasons.extend(f"risk:{item}" for item in risk.hard_reject_reasons)
    if risk.risk_score is None:
        reasons.append("risk_score_unknown")
    elif risk.risk_score > configuration.maximum_risk_score:
        reasons.append("risk_score_above_strategy_limit")
    if feature is None:
        reasons.append("feature_snapshot_unavailable")
        trade_count = 0
        unique_buyers = 0
        price_change = None
    else:
        universe_reason = paper_candidate_rejection(
            feature.price_evidence, lifecycle=feature.lifecycle.value
        )
        if universe_reason:
            reasons.append(universe_reason)
        metric = next(
            (
                item
                for item in feature.windows
                if item.window_seconds == configuration.scoring_window_seconds
            ),
            None,
        )
        trade_count = metric.trade_count if metric is not None else 0
        unique_buyers = metric.unique_buyers if metric is not None else 0
        price_change = metric.price_change_percent if metric is not None else None
        if metric is None:
            reasons.append("configured_scoring_window_unavailable")
        elif configuration.minimum_observation_seconds:
            if metric.observation_span_seconds < configuration.minimum_observation_seconds:
                reasons.append("insufficient_observation_span")
            if (
                metric.flow_imbalance is None
                or metric.flow_imbalance < configuration.minimum_flow_imbalance
            ):
                reasons.append("insufficient_sustained_buy_flow")
            if (
                metric.buyer_wallet_attribution_percent
                < configuration.minimum_buyer_attribution_percent
            ):
                reasons.append("buyer_attribution_incomplete")
            if (
                metric.largest_buyer_volume_share is None
                or metric.largest_buyer_volume_share > configuration.maximum_largest_buyer_share
            ):
                reasons.append("buyer_flow_concentrated")
            if configuration.require_sell_absorption and (
                metric.sell_count == 0 or (metric.price_change_percent or Decimal(0)) < 0
            ):
                reasons.append("sell_absorption_not_confirmed")
    if token_age is None:
        reasons.append("token_age_unknown")
    elif token_age < configuration.minimum_token_age_seconds:
        reasons.append("token_younger_than_strategy_minimum")
    if trade_count < configuration.minimum_trades_in_window:
        reasons.append("insufficient_trades_in_scoring_window")
    if unique_buyers < configuration.minimum_unique_buyers_in_window:
        reasons.append("insufficient_unique_buyers_in_scoring_window")
    if (
        price_change is not None
        and configuration.maximum_price_change_percent is not None
        and price_change > configuration.maximum_price_change_percent
    ):
        reasons.append("price_extension_above_entry_limit")
    if regime not in configuration.allowed_regimes:
        reasons.append("regime_not_allowed")
    if completeness < configuration.minimum_component_completeness_percent:
        reasons.append("score_component_completeness_below_minimum")
    blocking = bool(reasons)
    if not blocking and final_score is not None and final_score >= configuration.score_threshold:
        return StrategyDecisionAction.ENTER_CANDIDATE, (
            f"score_at_or_above_entry_threshold:{configuration.score_threshold}",
            "setup:post_graduation_continuation"
            if configuration.key == "conservative"
            else "setup:early_demand",
        )
    if not blocking and final_score is not None and final_score >= configuration.watch_threshold:
        return StrategyDecisionAction.WATCH, (
            f"score_at_or_above_watch_threshold:{configuration.watch_threshold}",
        )
    if not reasons:
        reasons.append("score_below_watch_threshold")
    return StrategyDecisionAction.SKIP, tuple(dict.fromkeys(reasons))
