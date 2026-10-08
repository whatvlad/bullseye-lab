from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import datetime
from decimal import Decimal
from math import ceil

from memebot.events.models import (
    DomainEvent,
    PaperOrderCompleted,
    ProviderHealthUpdated,
    StrategyDecisionCreated,
    TokenDiscovered,
    TokenRiskAssessed,
)


def distribution(values: list[float]) -> dict[str, float | int | None]:
    ordered = sorted(values)
    return {
        "samples": len(ordered),
        **{
            f"p{p}": ordered[max(0, ceil(len(ordered) * p / 100) - 1)] if ordered else None
            for p in (50, 90, 95, 99)
        },
    }


class EventMetrics:
    """Bounded rolling latency samples; counters since this process started.

    No mint/wallet labels. Historical totals belong to the durable database.
    """

    def __init__(self, sample_capacity: int = 2048) -> None:
        self._capacity = sample_capacity
        self._counts: Counter[str] = Counter()
        self._samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=self._capacity))
        self._fees = Decimal(0)

    def observe(self, event: DomainEvent, processing_at: datetime) -> None:
        self._counts[f"events:{event.event_type}"] += 1
        if event.source_timestamp_estimated:
            self._counts["source_timestamp_unknown_total"] += 1
        else:
            delay = (processing_at - event.source_event_at).total_seconds() * 1000
            if delay >= 0:
                self._samples["event_delay_ms"].append(delay)
            else:
                self._counts["future_source_timestamp_total"] += 1
        if isinstance(event, TokenDiscovered):
            self._counts["tokens_seen_total"] += 1
            # Legacy PumpPortal events also substituted reception for source time.
            if not event.source_timestamp_estimated and "pumpportal" not in event.provider.lower():
                received = event.provider_received_at or processing_at
                delay = (received - event.source_event_at).total_seconds() * 1000
                if delay >= 0:
                    self._samples["discovery_latency_ms"].append(delay)
        elif isinstance(event, TokenRiskAssessed) and event.result.allowed is False:
            self._counts["token_risk_rejections_total"] += 1
        elif isinstance(event, StrategyDecisionCreated):
            self._counts[f"decisions:{event.strategy_key}:{event.action.value}"] += 1
        elif isinstance(event, ProviderHealthUpdated):
            self._counts[f"provider_health:{event.provider}:{event.state.value}"] += 1
            if event.rate_limited:
                self._counts["rate_limit_events_total"] += 1
        elif isinstance(event, PaperOrderCompleted):
            self._counts[f"orders:{event.result.side.value}:{event.result.status.value}"] += 1
            fill = event.result.fill
            if fill is not None:
                self._fees += fill.total_fee_portfolio
                self._counts[
                    "entries_total" if event.result.side.value == "buy" else "exits_total"
                ] += 1
                self._samples["decision_to_fill_ms"].append(
                    (fill.filled_at - fill.decision_at).total_seconds() * 1000
                )
                self._samples["quote_age_at_fill_ms"].append(
                    (fill.filled_at - fill.quote_price_observed_at).total_seconds() * 1000
                )

    def snapshot(self) -> dict[str, object]:
        return {
            "scope": "since_process_start; latency percentiles over bounded recent samples",
            "counters": dict(self._counts),
            "fees_portfolio_currency": str(self._fees),
            "latency": {key: distribution(list(value)) for key, value in self._samples.items()},
        }
