from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable
from contextlib import suppress
from time import monotonic
from uuid import UUID, uuid5

from memebot.core.logging import get_logger
from memebot.eligibility import entry_rejection, paper_candidate_rejection, research_rejection
from memebot.events.models import (
    DomainEvent,
    TokenLifecycleChanged,
    TokenRiskAssessed,
    TokenTrade,
)
from memebot.paper.market_refresh import MarketSnapshotRefresher
from memebot.storage.database.registry import TokenRegistry

from .collector import SolanaRiskCollector
from .rules import RiskAssessor

_RISK_EVENT_NAMESPACE = UUID("08c6cd7a-24b5-57c2-9e4e-42a67d617a15")
type EventPublisher = Callable[[DomainEvent], Awaitable[object]]
type RiskTrigger = TokenLifecycleChanged | TokenTrade


class RiskAssessmentCoordinator:
    """Bound risk RPC work so websocket ingestion cannot grow tasks without limit."""

    def __init__(
        self,
        registry: TokenRegistry,
        collector: SolanaRiskCollector,
        assessor: RiskAssessor,
        publish: EventPublisher,
        *,
        worker_count: int,
        queue_size: int,
        reassessment_interval_seconds: int,
        max_assessments_per_hour: int,
        max_assessments_per_day: int,
        market_refresher: MarketSnapshotRefresher | None = None,
    ) -> None:
        self._registry = registry
        self._collector = collector
        self._assessor = assessor
        self._publish = publish
        self._market_refresher = market_refresher
        self._worker_count = worker_count
        self._queue: asyncio.Queue[RiskTrigger] = asyncio.Queue(queue_size)
        self._reassessment_interval_seconds = reassessment_interval_seconds
        self._max_assessments_per_hour = max_assessments_per_hour
        self._max_assessments_per_day = max_assessments_per_day
        self._assessment_times: deque[float] = deque()
        self._queued_mints: set[str] = set()
        self._last_scheduled_at: OrderedDict[str, float] = OrderedDict()
        self._last_lifecycle_key: OrderedDict[str, tuple[str, str, str | None]] = OrderedDict()
        self._history_capacity = max(10000, queue_size * 20)
        self._workers: list[asyncio.Task[None]] = []
        self._logger = get_logger("memebot.risk")

    async def start(self) -> None:
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._run_worker(index), name=f"risk-assessor-{index}")
            for index in range(self._worker_count)
        ]

    def enqueue(self, event: RiskTrigger) -> bool:
        if isinstance(event, TokenTrade):
            screen = paper_candidate_rejection if self._market_refresher else research_rejection
            if screen(event.normalized_state.evidence()) is not None:
                return True  # Excluded without consuming queue/RPC budget.
        elif isinstance(event, TokenLifecycleChanged) and (
            event.entry_rejection_reason
            or event.is_mayhem_mode is not False
            or event.lifecycle.value in {"graduation", "post_graduation", "mature"}
        ):
            return True
        force = False
        if isinstance(event, TokenLifecycleChanged):
            lifecycle_key = (
                event.lifecycle.value,
                event.validation_state.value,
                event.market,
            )
            force = self._last_lifecycle_key.get(event.mint) != lifecycle_key
            self._last_lifecycle_key[event.mint] = lifecycle_key
            self._last_lifecycle_key.move_to_end(event.mint)
            if len(self._last_lifecycle_key) > self._history_capacity:
                expired, _ = self._last_lifecycle_key.popitem(last=False)
                self._last_scheduled_at.pop(expired, None)
        if event.mint in self._queued_mints:
            return True
        now = monotonic()
        self._prune_budget(now)
        hourly = sum(item >= now - 3600 for item in self._assessment_times)
        if (self._max_assessments_per_hour > 0 and hourly >= self._max_assessments_per_hour) or (
            self._max_assessments_per_day > 0
            and len(self._assessment_times) >= self._max_assessments_per_day
        ):
            return True
        last_scheduled = self._last_scheduled_at.get(event.mint)
        if (
            not force
            and last_scheduled is not None
            and now - last_scheduled < self._reassessment_interval_seconds
        ):
            return True
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            return False
        self._queued_mints.add(event.mint)
        self._last_scheduled_at[event.mint] = now
        self._last_scheduled_at.move_to_end(event.mint)
        if len(self._last_scheduled_at) > self._history_capacity:
            expired, _ = self._last_scheduled_at.popitem(last=False)
            self._last_lifecycle_key.pop(expired, None)
        self._assessment_times.append(now)
        return True

    def _prune_budget(self, now: float) -> None:
        cutoff = now - 86400
        while self._assessment_times and self._assessment_times[0] < cutoff:
            self._assessment_times.popleft()

    async def close(self) -> None:
        if not self._workers:
            return
        try:
            async with asyncio.timeout(30):
                await self._queue.join()
        except TimeoutError:
            self._logger.warning("risk_assessment_drain_timeout", pending=self._queue.qsize())
        for task in self._workers:
            task.cancel()
        for task in self._workers:
            with suppress(asyncio.CancelledError):
                await task
        self._workers.clear()
        self._queued_mints.clear()
        self._last_scheduled_at.clear()
        self._last_lifecycle_key.clear()
        self._assessment_times.clear()

    async def _run_worker(self, index: int) -> None:
        while True:
            event = await self._queue.get()
            try:
                context = await self._registry.risk_context(event.mint)
                if context is None:
                    self._logger.warning("risk_context_missing", mint=event.mint, worker=index)
                    continue
                market = await self._registry.paper_market_context(
                    event.mint, as_of=event.source_event_at
                )
                if market is None:
                    continue
                if self._market_refresher is not None:
                    market = await self._market_refresher.refresh(market)
                    if market.rpc_state != "healthy" or market.execution_state is None:
                        continue
                if market.normalized_state is None:
                    continue
                if entry_rejection(
                    market.normalized_state.evidence(),
                    venue=market.venue.value,
                    lifecycle=market.lifecycle.value,
                    mayhem=market.is_mayhem_mode,
                    complete=market.curve_complete,
                ):
                    continue
                if not market.normalized_state.execution_identity_verified:
                    continue  # Canonical bootstrap is a separate bounded prerequisite duty.
                facts = await self._collector.collect(context)
                result = self._assessor.assess(context, facts)
                assessment = TokenRiskAssessed(
                    event_id=uuid5(_RISK_EVENT_NAMESPACE, str(event.event_id)),
                    provider="bullseye_risk_engine",
                    source_event_at=facts.observed_at,
                    provider_received_at=facts.observed_at,
                    correlation_id=event.correlation_id or event.event_id,
                    source_slot=facts.source_slot,
                    mint=event.mint,
                    trigger_event_id=event.event_id,
                    market=context.market,
                    result=result,
                    current_execution_state=(
                        {
                            **{
                                key: market.execution_state[key]
                                for key in ("slot", "curve", "rates", "binding")
                            },
                            "received_timestamp": market.received_timestamp.isoformat()
                            if market.received_timestamp
                            else None,
                            "basis": "pre-risk atomic verification; not final fill authorization",
                        }
                        if market.execution_state is not None
                        else None
                    ),
                )
                await self._publish(assessment)
            except Exception:
                self._logger.exception("risk_assessment_failed", mint=event.mint, worker=index)
            finally:
                self._queued_mints.discard(event.mint)
                self._queue.task_done()
