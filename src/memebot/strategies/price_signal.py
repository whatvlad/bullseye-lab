"""Required historical inputs of the existing momentum score, not execution proof."""

from decimal import Decimal

from memebot.events.models import MarketFeatureSnapshotCreated


def missing_price_inputs(
    feature: MarketFeatureSnapshotCreated | None,
    window: int,
    minimum_coverage_seconds: Decimal = Decimal(0),
) -> tuple[str, ...]:
    if feature is None:
        return (
            "decision_price",
            "rolling_price_change",
            "price_provenance",
            "price_window_coverage",
        )
    missing = []
    if feature.latest_price_raw is None or feature.latest_price_raw <= 0:
        missing.append("decision_price")
    metric = next((item for item in feature.windows if item.window_seconds == window), None)
    if metric is None or metric.price_change_percent is None:
        missing.append("rolling_price_change")
    evidence = feature.price_evidence
    if (
        evidence.get("observational_trust") != "OBSERVATIONAL_HEALTHY"
        or evidence.get("continuity_status") not in {"FIRST_OBSERVATION", "EXACT", "RPC_VALIDATED"}
        or evidence.get("state_semantics") != "POST_TRADE"
        or evidence.get("data_quality")
        not in {"source_time_reported", "canonical_atomic_bank_verified"}
    ):
        missing.append("price_provenance")
    if (
        metric is None
        or metric.price_sample_count < 2
        or metric.missing_price_sample_count
        or metric.price_observation_span_seconds <= 0
        or metric.price_observation_span_seconds < minimum_coverage_seconds
        or metric.open_price_raw is None
        or metric.open_price_raw <= 0
        or metric.close_price_raw is None
        or metric.close_price_raw <= 0
    ):
        missing.append("price_window_coverage")
    if metric is None or metric.flow_imbalance is None:
        missing.append("flow_imbalance")
    return tuple(missing)
