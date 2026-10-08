from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.eligibility import paper_candidate_rejection
from memebot.events.models import StrategyDecisionCreated
from memebot.providers.birdeye.client import BirdeyeClient, BirdeyeError
from memebot.storage.database.registry import TokenRegistry

_TAGS = ("dev", "insider", "bundler", "sniper", "smart_trader")


@dataclass(frozen=True, slots=True)
class AlphaFilterSnapshot:
    mint: str
    observed_at: datetime
    market_regime: str
    market_metrics: dict[str, Any]
    deployer_profile: dict[str, Any]
    holder_profile: dict[str, Any] | None
    shadow_reasons: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    shadow_mode: bool

    def payload(self) -> dict[str, Any]:
        return {
            "mint": self.mint,
            "observed_at": self.observed_at.isoformat(),
            "market_regime": self.market_regime,
            "market_metrics": _json_safe(self.market_metrics),
            "deployer_profile": _json_safe(self.deployer_profile),
            "holder_profile": _json_safe(self.holder_profile),
            "shadow_reasons": list(self.shadow_reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "shadow_mode": self.shadow_mode,
        }


class AlphaFilterService:
    """Candidate-only research filter; expensive enrichment is strictly budgeted."""

    def __init__(
        self,
        settings: Settings,
        registry: TokenRegistry,
        birdeye: BirdeyeClient | None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._birdeye = birdeye
        self._budget_day: date | None = None
        self._profiles_used = 0

    async def assess(self, decision: StrategyDecisionCreated) -> AlphaFilterSnapshot | None:
        if not self._settings.alpha_filter_enabled:
            return None
        if paper_candidate_rejection(decision.price_evidence) is not None:
            return None
        observed_at = utc_now()
        metrics = await self._registry.global_memecoin_metrics(as_of=observed_at)
        regime = _classify_market(metrics)
        context = await self._registry.risk_context(decision.mint)
        launches = context.creator_launches if context is not None else 0
        graduations = context.creator_graduations if context is not None else 0
        rejection_count = context.creator_rejections if context is not None else 0
        graduation_rate = Decimal(graduations) * 100 / Decimal(launches) if launches else None
        deployer = {
            "creator": context.creator if context is not None else None,
            "launches": launches,
            "graduations": graduations,
            "graduation_rate_percent": graduation_rate,
            "rejected_markets": rejection_count,
            "early_unique_buyers": context.early_unique_buyers if context else 0,
            "largest_early_buyer_share_percent": (
                context.largest_early_buyer_share_percent if context else None
            ),
            "largest_synchronized_buyer_group": (
                context.largest_synchronized_buyer_group if context else 0
            ),
        }
        shadow: list[str] = []
        blocking: list[str] = []
        if regime in {"risk_off", "unknown"}:
            shadow.append(f"global_market_{regime}")
        if launches >= 10 and (graduation_rate or Decimal(0)) < Decimal(5):
            blocking.append("serial_deployer_low_graduation_rate")
        if rejection_count >= 2:
            blocking.append("deployer_multiple_rejected_markets")

        holder = await self._holder_profile(decision.mint)
        if holder is None:
            shadow.append("holder_profile_unavailable")
        else:
            limits = {
                "dev": self._settings.alpha_max_dev_supply_percent,
                "insider": self._settings.alpha_max_insider_supply_percent,
                "bundler": self._settings.alpha_max_bundler_supply_percent,
                "sniper": self._settings.alpha_max_sniper_supply_percent,
            }
            for tag, limit in limits.items():
                share = _decimal(holder.get(tag))
                if share is not None and share >= limit:
                    blocking.append(f"{tag}_supply_above_limit")
            if (_decimal(holder.get("smart_trader")) or Decimal(0)) > 0:
                shadow.append("smart_trader_participation_observed")

        snapshot = AlphaFilterSnapshot(
            mint=decision.mint,
            observed_at=observed_at,
            market_regime=regime,
            market_metrics=metrics,
            deployer_profile=deployer,
            holder_profile=holder,
            shadow_reasons=tuple(dict.fromkeys(shadow)),
            blocking_reasons=tuple(dict.fromkeys(blocking)),
            shadow_mode=self._settings.alpha_filter_shadow_mode,
        )
        await self._registry.save_alpha_filter_snapshot(decision.mint, snapshot.payload())
        return snapshot

    async def _holder_profile(self, mint: str) -> dict[str, Any] | None:
        cached = await self._registry.alpha_filter_snapshot(mint)
        if cached is not None:
            observed = _datetime(cached.get("observed_at"))
            profile = cached.get("holder_profile")
            if (
                observed is not None
                and (utc_now() - observed).total_seconds()
                < self._settings.alpha_birdeye_cache_seconds
                and isinstance(profile, dict)
            ):
                return profile
        if self._birdeye is None or not self._take_budget_slot():
            return None
        try:
            payload = await self._birdeye.holder_profile(mint)
        except BirdeyeError:
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        tags = data.get("tags")
        result: dict[str, Any] = {}
        for tag in _TAGS:
            item = tags.get(tag) if isinstance(tags, dict) else None
            result[tag] = _supply_percent(item)
        result["top10"] = _supply_percent(data.get("top10_holder"))
        result["provider"] = "birdeye_holder_profile"
        return result

    def _take_budget_slot(self) -> bool:
        today = utc_now().date()
        if self._budget_day != today:
            self._budget_day = today
            self._profiles_used = 0
        if self._profiles_used >= self._settings.alpha_birdeye_holder_profiles_per_day:
            return False
        self._profiles_used += 1
        return True

    async def close(self) -> None:
        if self._birdeye is not None:
            await self._birdeye.close()


def _classify_market(metrics: dict[str, Any]) -> str:
    trades = int(metrics.get("trade_count_15m") or 0)
    buyers = int(metrics.get("unique_buyers_15m") or 0)
    launches = int(metrics.get("launches_15m") or 0)
    graduations = int(metrics.get("graduations_60m") or 0)
    buy_volume = _decimal(metrics.get("buy_volume_15m")) or Decimal(0)
    sell_volume = _decimal(metrics.get("sell_volume_15m")) or Decimal(0)
    if trades < 20 or buyers < 10:
        return "unknown"
    ratio = buy_volume / sell_volume if sell_volume > 0 else Decimal(10)
    if ratio < Decimal("0.75") or (launches >= 20 and graduations == 0):
        return "risk_off"
    if launches >= 100 and graduations >= 2 and ratio >= Decimal("1.8"):
        return "mania"
    if graduations >= 1 and ratio >= Decimal("1.15"):
        return "risk_on"
    return "selective"


def _supply_percent(item: object) -> Decimal | None:
    if isinstance(item, (str, int, float, Decimal)):
        return _decimal(item)
    if not isinstance(item, dict):
        return None
    for key in (
        "percent_of_supply",
        "percentage_of_supply",
        "supply_percent",
        "holding_percent",
        "percentage",
        "percent",
    ):
        if key in item:
            return _decimal(item[key])
    return None


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        return None
    return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)


def _json_safe(value: object) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
