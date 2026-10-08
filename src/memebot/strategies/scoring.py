from __future__ import annotations

from decimal import Decimal

from memebot.events.models import MarketFeatureSnapshotCreated
from memebot.models.common import DataAvailability
from memebot.models.risk import RiskResult
from memebot.models.strategy import (
    ScoreComponent,
    ScoreEvidence,
    ScoreResult,
    StrategyConfiguration,
    StrategyRegime,
)

from .price_signal import missing_price_inputs

_ZERO = Decimal(0)
_FIFTY = Decimal(50)
_HUNDRED = Decimal(100)


class TransparentScoreEngine:
    """Score only decision-time evidence and retain every component separately."""

    def score(
        self,
        feature: MarketFeatureSnapshotCreated | None,
        risk: RiskResult,
        configuration: StrategyConfiguration,
        *,
        regime: StrategyRegime,
    ) -> ScoreResult:
        weights = configuration.component_weights
        components = [
            self._momentum(feature, configuration),
            _missing(
                "wallet",
                weights["wallet"],
                "wallet_alpha_research_only_until_phase_9",
            ),
            self._risk(risk, weights["risk"]),
            _missing(
                "social",
                weights["social"],
                "social_weight_disabled"
                if not configuration.social_weight_enabled
                else "social_evidence_unavailable",
                unavailable=not configuration.social_weight_enabled,
            ),
            self._lifecycle(regime, weights["lifecycle"]),
            self._market(feature, weights["market"]),
        ]
        if "graduation_velocity" in weights:
            components.append(self._graduation_velocity(feature, configuration))
        enabled_weight = sum(
            (
                item.configured_weight
                for item in components
                if not (item.name == "social" and not configuration.social_weight_enabled)
            ),
            start=_ZERO,
        )
        available_weight = sum(
            (
                item.configured_weight
                for item in components
                if item.availability == DataAvailability.AVAILABLE
            ),
            start=_ZERO,
        )
        completeness = (
            available_weight * _HUNDRED / enabled_weight if enabled_weight > 0 else _ZERO
        ).quantize(Decimal("0.01"))
        scored: list[ScoreComponent] = []
        for item in components:
            if item.availability != DataAvailability.AVAILABLE or available_weight <= 0:
                scored.append(item)
                continue
            normalized_weight = (item.configured_weight * _HUNDRED / available_weight).quantize(
                Decimal("0.01")
            )
            contribution = (
                _required(item.score) * item.configured_weight / available_weight
            ).quantize(Decimal("0.01"))
            scored.append(
                item.model_copy(
                    update={
                        "normalized_weight": normalized_weight,
                        "contribution": contribution,
                    }
                )
            )
        final = (
            sum(
                (
                    _required(item.score) * item.configured_weight
                    for item in components
                    if item.availability == DataAvailability.AVAILABLE
                ),
                start=_ZERO,
            )
            / available_weight
            if available_weight > 0
            else None
        )
        return ScoreResult(
            final_score=final.quantize(Decimal("0.01")) if final is not None else None,
            component_completeness_percent=completeness,
            components=tuple(scored),
            overall_signal_completeness=completeness,
            missing_required_inputs=tuple(
                sorted(
                    {
                        key
                        for item in components
                        if item.configured_weight > 0
                        for key in item.missing_required_inputs
                    }
                )
            ),
        )

    @staticmethod
    def momentum_score(
        feature: MarketFeatureSnapshotCreated | None,
        window_seconds: int,
    ) -> Decimal | None:
        if feature is None:
            return None
        metric = next(
            (item for item in feature.windows if item.window_seconds == window_seconds),
            None,
        )
        if metric is None or metric.trade_count == 0:
            return None
        if missing_price_inputs(feature, window_seconds):
            return None
        values: list[Decimal] = []
        if metric.flow_imbalance is not None:
            values.append(_clamp(_FIFTY + _FIFTY * metric.flow_imbalance))
        if metric.price_change_percent is not None:
            values.append(_clamp(_FIFTY + metric.price_change_percent / Decimal(2)))
        acceleration_values = [
            _relative_direction_score(
                metric.volume_acceleration_quote_raw_per_second2 * Decimal(window_seconds),
                metric.volume_velocity_quote_raw_per_second,
            ),
            _relative_direction_score(
                metric.transaction_rate_acceleration_per_second2 * Decimal(window_seconds),
                metric.transaction_rate_per_second,
            ),
            _relative_direction_score(
                metric.unique_buyer_rate_acceleration_per_second2 * Decimal(window_seconds),
                metric.transaction_rate_per_second,
            ),
            _clamp(
                _FIFTY
                + _FIFTY
                * _clamp_unit(metric.buy_pressure_acceleration_per_second * Decimal(window_seconds))
            ),
        ]
        if metric.observation_span_seconds >= Decimal(window_seconds) / 2:
            values.extend(acceleration_values)
        return (sum(values, start=_ZERO) / Decimal(len(values))).quantize(Decimal("0.01"))

    def _momentum(
        self,
        feature: MarketFeatureSnapshotCreated | None,
        configuration: StrategyConfiguration,
    ) -> ScoreComponent:
        weight = configuration.component_weights["momentum"]
        missing = missing_price_inputs(
            feature,
            configuration.scoring_window_seconds,
            Decimal(configuration.minimum_observation_seconds),
        )
        if missing:
            return _missing(
                "momentum", weight, "required_historical_price_signal_incomplete"
            ).model_copy(
                update={"component_status": "INCOMPLETE", "missing_required_inputs": missing}
            )
        score = self.momentum_score(feature, configuration.scoring_window_seconds)
        if score is None:
            return _missing("momentum", weight, "required_window_or_trade_evidence_unavailable")
        metric = next(
            item
            for item in _required(feature).windows
            if item.window_seconds == configuration.scoring_window_seconds
        )
        return _available(
            "momentum",
            weight,
            score,
            (
                ScoreEvidence(
                    code="scoring_window_seconds",
                    value=metric.window_seconds,
                    message="Configured decision-time rolling window",
                ),
                ScoreEvidence(
                    code="trade_count",
                    value=metric.trade_count,
                    message="Trades observed in scoring window",
                ),
                ScoreEvidence(
                    code="flow_imbalance",
                    value=metric.flow_imbalance,
                    message="Buy/sell quote flow imbalance",
                ),
                ScoreEvidence(
                    code="price_change_percent",
                    value=metric.price_change_percent,
                    message="Decision-window raw price change",
                ),
                ScoreEvidence(
                    code="volume_acceleration",
                    value=metric.volume_acceleration_quote_raw_per_second2,
                    message="Decision-window quote-volume acceleration",
                ),
            ),
        )

    @staticmethod
    def _graduation_velocity(
        feature: MarketFeatureSnapshotCreated | None,
        configuration: StrategyConfiguration,
    ) -> ScoreComponent:
        weight = configuration.component_weights["graduation_velocity"]
        if feature is None or feature.bonding_progress_percent is None:
            return _missing(
                "graduation_velocity", weight, "bonding_progress_or_feature_unavailable"
            )
        metric = next(
            (
                item
                for item in feature.windows
                if item.window_seconds == configuration.scoring_window_seconds
            ),
            None,
        )
        if metric is None or metric.trade_count == 0:
            return _missing(
                "graduation_velocity", weight, "required_window_or_trade_evidence_unavailable"
            )
        if (
            metric.quote_reserve_velocity_raw_per_second is None
            or metric.buyer_wallet_attribution_percent < 60
            or metric.buyer_volume_hhi is None
            or metric.largest_buyer_volume_share is None
        ):
            return _missing(
                "graduation_velocity", weight, "reserve_velocity_or_buyer_attribution_unavailable"
            )
        values = [_clamp(feature.bonding_progress_percent)]
        if metric.flow_imbalance is not None:
            values.append(_clamp(_FIFTY + _FIFTY * metric.flow_imbalance))
        if metric.quote_reserve_velocity_raw_per_second is not None:
            values.append(
                _relative_direction_score(
                    metric.quote_reserve_velocity_raw_per_second,
                    metric.volume_velocity_quote_raw_per_second,
                )
            )
        concentration_is_usable = metric.buyer_wallet_attribution_percent >= Decimal(60)
        if metric.buyer_volume_hhi is not None and concentration_is_usable:
            values.append(_clamp(_HUNDRED * (Decimal(1) - metric.buyer_volume_hhi)))
        if metric.largest_buyer_volume_share is not None and concentration_is_usable:
            values.append(_clamp(_HUNDRED * (Decimal(1) - metric.largest_buyer_volume_share)))
        score = (sum(values, start=_ZERO) / Decimal(len(values))).quantize(Decimal("0.01"))
        return _available(
            "graduation_velocity",
            weight,
            score,
            (
                ScoreEvidence(
                    code="bonding_progress_percent",
                    value=feature.bonding_progress_percent,
                    message="Decision-time Pump bonding-curve progress",
                ),
                ScoreEvidence(
                    code="quote_reserve_velocity_raw_per_second",
                    value=metric.quote_reserve_velocity_raw_per_second,
                    message="Net real-SOL reserve accumulation velocity",
                ),
                ScoreEvidence(
                    code="buyer_wallet_attribution_percent",
                    value=metric.buyer_wallet_attribution_percent,
                    message="Share of buy volume with an attributable wallet",
                ),
                ScoreEvidence(
                    code="buyer_volume_hhi",
                    value=metric.buyer_volume_hhi,
                    message="Lower values indicate more distributed buyer flow",
                ),
                ScoreEvidence(
                    code="largest_buyer_volume_share",
                    value=metric.largest_buyer_volume_share,
                    message="Largest observed buyer share of attributed buy volume",
                ),
            ),
        )

    @staticmethod
    def _risk(risk: RiskResult, weight: Decimal) -> ScoreComponent:
        if risk.risk_score is None or risk.allowed is not True:
            return _missing("risk", weight, "risk_gate_not_approved_or_score_unknown")
        return _available(
            "risk",
            weight,
            _HUNDRED - risk.risk_score,
            (
                ScoreEvidence(
                    code="risk_score",
                    value=risk.risk_score,
                    message="Phase 3 risk score; lower is safer",
                ),
                ScoreEvidence(
                    code="risk_data_completeness_percent",
                    value=risk.data_completeness_percent,
                    message="Phase 3 evidence completeness",
                ),
            ),
        )

    @staticmethod
    def _lifecycle(regime: StrategyRegime, weight: Decimal) -> ScoreComponent:
        scores = {
            StrategyRegime.NEW_LAUNCH: Decimal(55),
            StrategyRegime.EARLY_MOMENTUM: Decimal(85),
            StrategyRegime.BONDING_CURVE: Decimal(65),
            StrategyRegime.FINAL_STRETCH: Decimal(90),
            StrategyRegime.GRADUATION: Decimal(85),
            StrategyRegime.POST_GRADUATION: Decimal(75),
            StrategyRegime.MATURE_MOMENTUM: Decimal(65),
            StrategyRegime.DEAD_OR_ILLIQUID: Decimal(0),
        }
        score = scores.get(regime)
        if score is None:
            return _missing("lifecycle", weight, "strategy_regime_unknown")
        return _available(
            "lifecycle",
            weight,
            score,
            (ScoreEvidence(code="regime", value=regime.value, message="Classified regime"),),
        )

    @staticmethod
    def _market(feature: MarketFeatureSnapshotCreated | None, weight: Decimal) -> ScoreComponent:
        if feature is None:
            return _missing("market", weight, "feature_snapshot_unavailable")
        verified = feature.validation_state.value == "verified_market_data"
        score = Decimal(100) if verified else Decimal(0)
        return _available(
            "market",
            weight,
            score,
            (
                ScoreEvidence(
                    code="market_validation_state",
                    value=feature.validation_state.value,
                    message="Deterministic market validation state",
                ),
            ),
        )


def _available(
    name: str,
    weight: Decimal,
    score: Decimal,
    evidence: tuple[ScoreEvidence, ...],
) -> ScoreComponent:
    return ScoreComponent(
        name=name,
        availability=DataAvailability.AVAILABLE,
        component_status="COMPLETE",
        score=_clamp(score),
        configured_weight=weight,
        evidence=evidence,
    )


def _missing(
    name: str,
    weight: Decimal,
    reason: str,
    *,
    unavailable: bool = False,
) -> ScoreComponent:
    return ScoreComponent(
        name=name,
        availability=(DataAvailability.UNAVAILABLE if unavailable else DataAvailability.UNKNOWN),
        configured_weight=weight,
        reason=reason,
        component_status="UNAVAILABLE" if unavailable else "INCOMPLETE",
    )


def _relative_direction_score(value: Decimal, scale: Decimal) -> Decimal:
    denominator = abs(value) + abs(scale)
    ratio = value / denominator if denominator > 0 else _ZERO
    return _clamp(_FIFTY + _FIFTY * ratio)


def _clamp(value: Decimal) -> Decimal:
    return min(_HUNDRED, max(_ZERO, value))


def _clamp_unit(value: Decimal) -> Decimal:
    return min(Decimal(1), max(Decimal(-1), value))


def _required[ValueT](value: ValueT | None) -> ValueT:
    if value is None:
        raise ValueError("required strategy evidence is missing")
    return value
