from __future__ import annotations

from decimal import Decimal

from memebot.models.market import MarketLifecycle
from memebot.models.strategy import StrategyRegime


def classify_regime(
    lifecycle: MarketLifecycle,
    *,
    token_age_seconds: int | None,
    momentum_score: Decimal | None,
) -> StrategyRegime:
    if lifecycle == MarketLifecycle.DEAD_OR_ILLIQUID:
        return StrategyRegime.DEAD_OR_ILLIQUID
    if lifecycle == MarketLifecycle.POST_GRADUATION:
        return StrategyRegime.POST_GRADUATION
    if lifecycle == MarketLifecycle.GRADUATION:
        return StrategyRegime.GRADUATION
    if lifecycle == MarketLifecycle.FINAL_STRETCH:
        return StrategyRegime.FINAL_STRETCH
    if lifecycle == MarketLifecycle.MATURE:
        return StrategyRegime.MATURE_MOMENTUM
    if lifecycle == MarketLifecycle.NEW_LAUNCH:
        return StrategyRegime.NEW_LAUNCH
    if lifecycle == MarketLifecycle.BONDING_CURVE:
        if (
            token_age_seconds is not None
            and token_age_seconds <= 120
            and momentum_score is not None
            and momentum_score >= Decimal(65)
        ):
            return StrategyRegime.EARLY_MOMENTUM
        return StrategyRegime.BONDING_CURVE
    return StrategyRegime.UNKNOWN
