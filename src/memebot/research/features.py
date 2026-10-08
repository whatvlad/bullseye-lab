from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from math import sqrt
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

from memebot.core.config import Settings
from memebot.research.forensics import number
from memebot.storage.database.engine import create_database_engine
from memebot.storage.database.models import DecisionOutcomeRecord

FEATURES = (
    "unique_buyer_rate_acceleration_per_second2",
    "volume_acceleration_quote_raw_per_second2",
    "price_acceleration_percent_per_second2",
    "buy_sell_volume_ratio",
    "real_quote_reserve_velocity_raw_per_second",
)
HORIZONS = (5, 10, 30, 60, 120, 300, 600)


def correlation(pairs: list[tuple[float, float, str]]) -> dict[str, Any]:
    count = len(pairs)
    if count < 3:
        return {"samples": count, "unique_tokens": len({p[2] for p in pairs}), "pearson": None}
    mean_x = sum(p[0] for p in pairs) / count
    mean_y = sum(p[1] for p in pairs) / count
    covariance = sum((x - mean_x) * (y - mean_y) for x, y, _mint in pairs)
    variance_x = sum((x - mean_x) ** 2 for x, _y, _mint in pairs)
    variance_y = sum((y - mean_y) ** 2 for _x, y, _mint in pairs)
    return {
        "samples": count,
        "unique_tokens": len({p[2] for p in pairs}),
        "pearson": covariance / sqrt(variance_x * variance_y)
        if variance_x > 0 and variance_y > 0
        else None,
        "mean_forward_mark_return_percent": mean_y,
    }


def analyze_rows(
    rows: list[dict[str, Any]], train_end: datetime, validation_end: datetime
) -> dict[str, Any]:
    if train_end.tzinfo is None or validation_end.tzinfo is None or validation_end <= train_end:
        raise ValueError("temporal boundaries must be aware and increasing")
    first_seen: dict[str, datetime] = {}
    for row in rows:
        stamp = _aware(row["decided_at"])
        first_seen[row["mint"]] = min(first_seen.get(row["mint"], stamp), stamp)
    pairs: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    coverage: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        stamp = _aware(row["decided_at"])
        cohort = first_seen[row["mint"]]
        split = (
            "train" if cohort < train_end else ("validation" if cohort < validation_end else "test")
        )
        end = train_end if split == "train" else validation_end if split == "validation" else None
        if end is not None and stamp >= end:
            continue
        snapshot = row.get("feature_snapshot_json") or {}
        identity = (row["mint"], str(snapshot.get("event_id") or row["decision_event_id"]))
        if identity in seen:
            continue
        seen.add(identity)
        observed_at = snapshot.get("observed_at")
        if observed_at is None or _aware(datetime.fromisoformat(observed_at)) > stamp:
            coverage[f"{split}:feature_unknown_or_future"] += 1
            continue
        windows = snapshot.get("windows") or []
        eligible = [window for window in windows if window.get("window_seconds", 0) <= 30]
        metric: dict[str, Any] = max(
            eligible, key=lambda window: window["window_seconds"], default={}
        )
        for horizon in HORIZONS:
            label = f"{split}:{horizon}s"
            coverage[f"{label}:eligible"] += 1
            if end is not None and stamp + timedelta(seconds=horizon) >= end:
                coverage[f"{label}:purged_boundary"] += 1
                continue
            result = (row.get("horizon_returns_json") or {}).get(str(horizon))
            if not isinstance(result, dict):
                coverage[f"{label}:missing"] += 1
                continue
            if result.get("coverage") != "observed":
                quality = "gap" if result.get("coverage") == "gap" else "unknown_quality"
                coverage[f"{label}:{quality}"] += 1
                continue
            future_return = number(result.get("return_percent"))
            if future_return is None:
                coverage[f"{label}:missing_return"] += 1
                continue
            coverage[f"{label}:observed"] += 1
            for feature in FEATURES:
                value = number(metric.get(feature))
                if value is not None:
                    pairs[f"{label}:{feature}"].append(
                        (float(value), float(future_return), row["mint"])
                    )
    return {
        "train_end": train_end.isoformat(),
        "validation_end": validation_end.isoformat(),
        "coverage": dict(coverage),
        "correlations": {key: correlation(value) for key, value in pairs.items()},
        "limitations": [
            "mark returns before execution costs; not net expectancy",
            "repeated token observations are dependent; samples are not independent trades",
            "missing horizons and gaps excluded, never replaced by zero",
            "tokens assigned to earliest cohort, horizon labels purged at split boundaries",
            "historical diagnostic splits; no prospective profitability validation",
        ],
    }


async def analyze_database(train_end: datetime, validation_end: datetime) -> dict[str, Any]:
    engine = create_database_engine(Settings().database_url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.execute(text("SET LOCAL statement_timeout = '60s'"))
            result = await connection.execute(
                select(
                    DecisionOutcomeRecord.decision_event_id,
                    DecisionOutcomeRecord.mint,
                    DecisionOutcomeRecord.decided_at,
                    DecisionOutcomeRecord.feature_snapshot_json,
                    DecisionOutcomeRecord.horizon_returns_json,
                ).order_by(
                    DecisionOutcomeRecord.decided_at, DecisionOutcomeRecord.decision_event_id
                )
            )
            rows = [dict(row) for row in result.mappings()]
        return await asyncio.to_thread(analyze_rows, rows, train_end, validation_end)
    finally:
        await engine.dispose()


def _aware(stamp: datetime) -> datetime:
    return stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)


def main() -> None:
    parser = argparse.ArgumentParser(description="Temporal feature/forward-mark-return research")
    parser.add_argument("--train-end", type=datetime.fromisoformat, required=True)
    parser.add_argument("--validation-end", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = asyncio.run(analyze_database(args.train_end, args.validation_end))
    except Exception as error:
        parser.exit(1, f"Feature report failed: {type(error).__name__}\n")
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "coverage": report["coverage"]}, indent=2))


if __name__ == "__main__":
    main()
