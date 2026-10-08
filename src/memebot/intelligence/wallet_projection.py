"""Optional wallet research pulls durable work; market ingestion only wakes it."""

import asyncio
from collections.abc import Awaitable, Callable


class DurableWalletProjector:
    def __init__(
        self,
        project_batch: Callable[[], Awaitable[int]],
        on_failure: Callable[[Exception], None],
        *,
        poll_seconds: float = 5,
        work_interval_seconds: float = 2,
    ) -> None:
        self._project_batch = project_batch
        self._on_failure = on_failure
        self._poll_seconds = poll_seconds
        self._work_interval_seconds = work_interval_seconds
        self._wake = asyncio.Event()

    def wake(self) -> None:
        # This signal carries no events. Unprojected events stay in PostgreSQL,
        # so neither saturation nor process restart can discard the work.
        self._wake.set()

    async def run(self) -> None:
        while True:
            self._wake.clear()
            try:
                processed = await self._project_batch()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self._on_failure(error)
                await asyncio.sleep(self._poll_seconds)
                continue
            if processed:
                # Optional historical research yields database/CPU capacity to
                # live prices and position exits even when durable backlog grows.
                await asyncio.sleep(self._work_interval_seconds)
                continue
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self._poll_seconds)
            except TimeoutError:
                pass
