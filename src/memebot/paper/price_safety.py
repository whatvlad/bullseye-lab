"""Entry availability is stricter than exit availability. Unknown never means zero age."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from memebot.core.config import Settings
from memebot.eligibility import entry_rejection
from memebot.models.paper import PaperOrderResult

from .models import ExecutionMarketSnapshot


def price_metadata(market: ExecutionMarketSnapshot, now: datetime) -> dict[str, Any]:
    def age(timestamp: datetime | None) -> int | None:
        return int((now - timestamp).total_seconds() * 1000) if timestamp else None

    return {
        "price_source": market.price_source,
        "source_timestamp": market.source_timestamp,
        "received_timestamp": market.received_timestamp,
        "price_age_ms": age(market.source_timestamp),
        "received_age_ms": age(market.received_timestamp),
        "feed_age_ms": age(market.feed_timestamp),
        "price_source_disagreement_pct": market.price_source_disagreement_pct,
        "data_quality": market.data_quality,
        "feed_timestamp_estimated": market.feed_timestamp_estimated,
        **(market.normalized_state.evidence() if market.normalized_state else {}),
    }


def entry_data_block(
    market: ExecutionMarketSnapshot, now: datetime, settings: Settings
) -> str | None:
    evidence = price_metadata(market, now)
    universe_reason = entry_rejection(
        evidence,
        venue=market.venue.value,
        lifecycle=market.lifecycle.value,
        mayhem=market.is_mayhem_mode,
        complete=market.curve_complete,
    )
    if universe_reason:
        return universe_reason
    if market.normalized_state is not None and market.normalized_state.state_quality != "HEALTHY":
        return "normalized_state_not_execution_ready"
    if market.execution_state is not None:
        received_age = evidence["received_age_ms"]
        if (
            received_age is None
            or not 0 <= received_age <= settings.paper_max_market_staleness_seconds * 1000
        ):
            return "stale_current_execution_state"
        if market.rpc_state != "healthy":
            return "entry_rpc_degraded"
        if not executable_reserves(market):
            return "entry_executable_quote_incomplete"
        limit = settings.paper_entry_max_source_disagreement_percent
        if (
            limit is not None
            and market.price_source_disagreement_pct is not None
            and market.price_source_disagreement_pct > limit
        ):
            return "entry_price_sources_disagree"
        return None
    feed_age = evidence["feed_age_ms"]
    if feed_age is None or feed_age < 0:
        return "feed_timestamp_unknown_or_future"
    if feed_age > settings.paper_entry_max_feed_age_seconds * 1000:
        return "entry_feed_stale"
    if market.feed_timestamp_estimated and not settings.paper_entry_allow_estimated_feed_time:
        return "entry_feed_source_time_unknown"
    if market.price_source == "unknown" or market.data_quality == "unknown":
        return "price_provenance_unknown"
    if settings.paper_entry_require_rpc and market.rpc_state != "healthy":
        return "entry_rpc_degraded"
    disagreement = market.price_source_disagreement_pct
    limit = settings.paper_entry_max_source_disagreement_percent
    if not executable_reserves(market):
        return "entry_executable_quote_incomplete"
    if limit is None:
        return "entry_disagreement_limit_unconfigured"
    if disagreement is None:
        return "entry_source_comparison_unavailable"
    if limit is not None and disagreement is not None and disagreement > limit:
        return "entry_price_sources_disagree"
    return None


def executable_reserves(market: ExecutionMarketSnapshot) -> bool:
    from .execution import _reserves

    return (
        _reserves(market) is not None
        and market.real_token_reserves_raw is not None
        and market.real_quote_reserves_raw is not None
        and not market.curve_complete
    )


def source_disagreement(reference: Decimal | None, price: Decimal) -> Decimal | None:
    return abs(price / reference - 1) * 100 if reference and reference > 0 else None


def with_price_evidence(
    result: PaperOrderResult, market: ExecutionMarketSnapshot | None, now: datetime
) -> PaperOrderResult:
    evidence: dict[str, Any] = (
        price_metadata(market, now)
        if market
        else {
            "price_source": "unavailable",
            "source_timestamp": None,
            "received_timestamp": None,
            "price_age_ms": None,
            "feed_age_ms": None,
            "price_source_disagreement_pct": None,
            "data_quality": "unavailable",
        }
    )
    fill = result.fill
    if fill is not None:
        for name in (
            "price_source",
            "source_timestamp",
            "received_timestamp",
            "price_age_ms",
            "feed_age_ms",
            "price_source_disagreement_pct",
            "data_quality",
            "feed_timestamp_estimated",
            "received_age_ms",
            "state_source",
            "state_semantics",
            "state_quality",
            "state_slot",
            "reconciled_at",
            "continuity_status",
            "state_reason",
            "identity_verified",
            "observational_trust",
            "program",
            "is_mayhem_mode",
            "multi_event_ambiguous",
            "trading_universe",
            "entry_eligibility_status",
            "entry_rejection_reason",
            "execution_identity_verified",
            "execution_config_verified",
            "execution_assumptions_verified",
            "invalidation_scope",
            "invalidation_reason",
        ):
            evidence[name] = getattr(fill, name)
    for name in (
        "decision_price",
        "reference_price",
        "executable_quote",
        "simulated_fill",
        "price_impact",
        "slippage",
        "fees",
    ):
        evidence[name] = getattr(fill, name) if fill else None
    if fill is None and market is not None:
        evidence["decision_price"] = market.decision_price or market.observed_price_raw
        evidence["reference_price"] = market.observed_price_raw
    return result.model_copy(update={"price_evidence": evidence})
