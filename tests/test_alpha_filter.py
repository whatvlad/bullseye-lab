from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from memebot.core.config import Settings
from memebot.events.models import StrategyDecisionCreated
from memebot.intelligence.alpha_filter import AlphaFilterService
from memebot.intelligence.risk.models import LocalRiskContext
from memebot.models.market import MarketLifecycle, MarketValidationState
from memebot.models.strategy import ScoreResult, StrategyDecisionAction, StrategyRegime
from standard_evidence import approved_evidence

MINT = "So11111111111111111111111111111111111111112"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


def _decision(mint: str = MINT) -> StrategyDecisionCreated:
    return StrategyDecisionCreated(
        event_id=UUID(int=1),
        provider="test",
        source_event_at=NOW,
        mint=mint,
        strategy_key="balanced",
        strategy_version_id=UUID(int=2),
        active_strategy=True,
        action=StrategyDecisionAction.ENTER_CANDIDATE,
        regime=StrategyRegime.EARLY_MOMENTUM,
        risk_event_id=UUID(int=3),
        score=ScoreResult(
            final_score=Decimal(80),
            component_completeness_percent=Decimal(100),
            components=(),
        ),
        price_evidence=approved_evidence(),
        reasons=("test",),
    )


@pytest.mark.asyncio
async def test_alpha_filter_extracts_holder_cohorts_and_blocks_concentration() -> None:
    saved: dict[str, object] = {}

    class Registry:
        async def global_memecoin_metrics(self, *, as_of: datetime) -> dict[str, object]:
            return {
                "trade_count_15m": 1000,
                "unique_buyers_15m": 200,
                "launches_15m": 50,
                "graduations_60m": 3,
                "buy_volume_15m": "200",
                "sell_volume_15m": "100",
            }

        async def risk_context(self, mint: str) -> LocalRiskContext:
            return LocalRiskContext(
                mint,
                "11111111111111111111111111111111",
                None,
                None,
                MarketLifecycle.BONDING_CURVE,
                MarketValidationState.VERIFIED_MARKET_DATA,
                NOW,
                1,
                20,
                0,
                2,
                20,
                Decimal(15),
                4,
            )

        async def alpha_filter_snapshot(self, mint: str) -> None:
            return None

        async def save_alpha_filter_snapshot(self, mint: str, payload: dict[str, object]) -> None:
            saved.update(payload)

    class Birdeye:
        async def holder_profile(self, mint: str) -> dict[str, object]:
            return {
                "success": True,
                "data": {
                    "tags": {
                        "dev": {"percent_of_supply": "25"},
                        "insider": {"percent_of_supply": "3"},
                        "bundler": {"percent_of_supply": "45"},
                        "sniper": {"percent_of_supply": "8"},
                        "smart_trader": {"percent_of_supply": "1.5"},
                    },
                    "top10_holder": {"percent_of_supply": "67"},
                },
            }

        async def close(self) -> None:
            return None

    service = AlphaFilterService(
        Settings(_env_file=None),
        Registry(),  # type: ignore[arg-type]
        Birdeye(),  # type: ignore[arg-type]
    )
    snapshot = await service.assess(_decision())

    assert snapshot is not None
    assert snapshot.market_regime == "risk_on"
    assert snapshot.holder_profile is not None
    assert snapshot.holder_profile["top10"] == Decimal(67)
    assert snapshot.blocking_reasons == (
        "serial_deployer_low_graduation_rate",
        "deployer_multiple_rejected_markets",
        "dev_supply_above_limit",
        "bundler_supply_above_limit",
    )
    assert "serial_deployer_low_graduation_rate" not in snapshot.shadow_reasons
    assert saved["market_regime"] == "risk_on"
