"""Batched background persistence for high-volume market events.

The live decision path must not wait for one database transaction per trade
(~11 ms through Docker on Windows, measured 2026-10-08, which capped ingestion
below the feed's peak rate). Trades are queued here and stored in batches, one
transaction per batch, in submission order. Nothing is dropped: a failed batch is
retried until it is stored.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from memebot.core.logging import get_logger
from memebot.events.models import DomainEvent

type BatchStore = Callable[[list[DomainEvent]], Awaitable[None]]


class WriteBehindWriter:
    def __init__(
        self,
        store: BatchStore,
        *,
        max_batch: int = 250,
        max_delay_seconds: float = 0.02,
        retry_seconds: float = 1.0,
    ) -> None:
        self._store = store
        self._max_batch = max_batch
        self._max_delay = max_delay_seconds
        self._retry = retry_seconds
        self._pending: deque[DomainEvent] = deque()
        self._wake = asyncio.Event()
        self._written = asyncio.Condition()
        self.submitted = 0
        self.written = 0
        self.metrics: dict[str, Any] = {"batches": 0, "failures": 0, "pending_peak": 0}
        self._logger = get_logger("memebot.write_behind")

    def submit(self, event: DomainEvent) -> int:
        self._pending.append(event)
        self.submitted += 1
        self.metrics["pending_peak"] = max(self.metrics["pending_peak"], len(self._pending))
        self._wake.set()
        return self.submitted

    @property
    def pending(self) -> int:
        return len(self._pending)

    async def wait_written(self, sequence: int, limit_seconds: float) -> bool:
        """Wait until every event up to `sequence` is stored (False on timeout)."""
        try:
            async with asyncio.timeout(limit_seconds):
                async with self._written:
                    await self._written.wait_for(lambda: self.written >= sequence)
            return True
        except TimeoutError:
            return False

    async def run(self) -> None:
        while True:
            await self._wake.wait()
            await asyncio.sleep(self._max_delay)  # let a burst accumulate
            self._wake.clear()
            while self._pending:
                batch = [
                    self._pending[index] for index in range(min(self._max_batch, self.pending))
                ]
                started = perf_counter()
                try:
                    await self._store(batch)
                except Exception as error:
                    self.metrics["failures"] += 1
                    self._logger.error(
                        "write_behind_batch_failed",
                        error_type=type(error).__name__,
                        pending=self.pending,
                    )
                    await asyncio.sleep(self._retry)
                    continue
                for _ in batch:
                    self._pending.popleft()
                self.metrics["batches"] += 1
                self.metrics["last_batch_size"] = len(batch)
                self.metrics["last_batch_ms"] = round((perf_counter() - started) * 1000, 1)
                async with self._written:
                    self.written += len(batch)
                    self._written.notify_all()

    async def flush(self, limit_seconds: float = 30) -> bool:
        self._wake.set()
        return await self.wait_written(self.submitted, limit_seconds)
