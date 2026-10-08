from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID, uuid5

from memebot.models.strategy import StrategyConfiguration, StrategyRegime

_CONFIGURATION_NAMESPACE = UUID("934386da-392b-5a55-bf71-3655e0106907")
_WEIGHTS = {
    "momentum": Decimal(70),
    "wallet": Decimal(0),
    "risk": Decimal(0),
    "social": Decimal(0),
    "lifecycle": Decimal(0),
    "market": Decimal(0),
    "graduation_velocity": Decimal(30),
}


def initial_strategy_presets() -> tuple[StrategyConfiguration, ...]:
    return (
        _preset(
            key="conservative",
            display_name="Conservative",
            active=False,
            score_threshold=Decimal(80),
            watch_threshold=Decimal(70),
            maximum_risk_score=Decimal(30),
            minimum_completeness=Decimal(70),
            minimum_age=30,
            minimum_trades=15,
            minimum_unique_buyers=8,
            maximum_price_change=Decimal(25),
            window=60,
            regimes=frozenset(
                {
                    StrategyRegime.POST_GRADUATION,
                    StrategyRegime.MATURE_MOMENTUM,
                }
            ),
        ),
        _preset(
            key="balanced",
            display_name="Balanced",
            active=False,
            score_threshold=Decimal(60),
            watch_threshold=Decimal(50),
            maximum_risk_score=Decimal(60),
            minimum_completeness=Decimal(50),
            minimum_age=10,
            minimum_trades=10,
            minimum_unique_buyers=6,
            maximum_price_change=Decimal(35),
            window=30,
            regimes=frozenset(
                {
                    StrategyRegime.BONDING_CURVE,
                    StrategyRegime.EARLY_MOMENTUM,
                    StrategyRegime.FINAL_STRETCH,
                }
            ),
        ),
        _preset(
            key="aggressive",
            display_name="Aggressive",
            active=True,
            score_threshold=Decimal(55),
            watch_threshold=Decimal(45),
            maximum_risk_score=Decimal(70),
            minimum_completeness=Decimal(50),
            minimum_age=3,
            minimum_trades=5,
            minimum_unique_buyers=3,
            maximum_price_change=Decimal(50),
            window=10,
            regimes=frozenset(
                {
                    StrategyRegime.NEW_LAUNCH,
                    StrategyRegime.BONDING_CURVE,
                    StrategyRegime.EARLY_MOMENTUM,
                    StrategyRegime.FINAL_STRETCH,
                }
            ),
        ),
    )


def _preset(
    *,
    key: str,
    display_name: str,
    active: bool,
    score_threshold: Decimal,
    watch_threshold: Decimal,
    maximum_risk_score: Decimal,
    minimum_completeness: Decimal,
    minimum_age: int,
    minimum_trades: int,
    minimum_unique_buyers: int,
    maximum_price_change: Decimal,
    window: int,
    regimes: frozenset[StrategyRegime],
    weights: dict[str, Decimal] = _WEIGHTS,
) -> StrategyConfiguration:
    payload = {
        "key": key,
        "version": 10 if key == "aggressive" else 9,
        "minimum_observation_seconds": 3 if key == "aggressive" else min(15, window // 2),
        "require_sell_absorption": key != "aggressive",
        "score_threshold": str(score_threshold),
        "watch_threshold": str(watch_threshold),
        "maximum_risk_score": str(maximum_risk_score),
        "minimum_completeness": str(minimum_completeness),
        "minimum_age": minimum_age,
        "minimum_trades": minimum_trades,
        "minimum_unique_buyers": minimum_unique_buyers,
        "maximum_price_change": str(maximum_price_change),
        "window": window,
        "regimes": sorted(item.value for item in regimes),
        "weights": {name: str(value) for name, value in sorted(weights.items())},
        "social_weight_enabled": False,
    }
    if key == "aggressive":
        payload.update(
            minimum_flow_imbalance="0.10",
            minimum_buyer_attribution_percent="70",
            maximum_largest_buyer_share="0.65",
        )
    version_id = uuid5(
        _CONFIGURATION_NAMESPACE,
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
    )
    return StrategyConfiguration(
        version_id=version_id,
        key=key,
        display_name=display_name,
        version=10 if key == "aggressive" else 9,
        minimum_observation_seconds=3 if key == "aggressive" else min(15, window // 2),
        minimum_flow_imbalance=Decimal("0.10") if key == "aggressive" else Decimal("0.20"),
        minimum_buyer_attribution_percent=Decimal(70) if key == "aggressive" else Decimal(80),
        maximum_largest_buyer_share=Decimal("0.65") if key == "aggressive" else Decimal("0.50"),
        require_sell_absorption=key != "aggressive",
        active_for_execution=active,
        score_threshold=score_threshold,
        watch_threshold=watch_threshold,
        maximum_risk_score=maximum_risk_score,
        minimum_component_completeness_percent=minimum_completeness,
        minimum_token_age_seconds=minimum_age,
        minimum_trades_in_window=minimum_trades,
        minimum_unique_buyers_in_window=minimum_unique_buyers,
        maximum_price_change_percent=maximum_price_change,
        scoring_window_seconds=window,
        allowed_regimes=regimes,
        component_weights=dict(weights),
        social_weight_enabled=False,
    )
