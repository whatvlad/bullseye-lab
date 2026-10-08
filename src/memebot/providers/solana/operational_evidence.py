"""Nonblocking reuse of the existing bounded full-packet transport.

Missing/late packets retain the native UNKNOWN guard after a bounded wait.
No replay, RPC transaction fetch, or COMPLETE_FOR_WINDOW claim is introduced.
"""

from __future__ import annotations

import asyncio
import json
import traceback
from collections import Counter, OrderedDict
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any

from pydantic import ValidationError

from memebot.core.clock import utc_now
from memebot.core.logging import get_logger
from memebot.events.models import DomainEvent, TokenDiscovered, TokenLifecycleChanged, TokenTrade
from memebot.models.market import LaunchVenue, MarketLifecycle
from memebot.providers.solana.alchemy_evidence import (
    AlchemyTransactionEvidenceStream,
    FullStreamBudgetExceeded,
)
from memebot.providers.solana.canonical import curve_address
from memebot.providers.solana.evidence_stream import EvidenceBuffer, TransactionEvidence
from memebot.providers.solana.pump_idl import NATIVE_SOL_MINT, WRAPPED_SOL_MINT
from memebot.providers.solana.stream_budget import RollingStreamBudget
from memebot.research.early_watch import EarlyWatch


class OperationalEvidenceCache:
    def __init__(
        self,
        token: str,
        *,
        max_bytes: int = 32_000_000,
        process_packet: Callable[[TransactionEvidence], Awaitable[None]] | None = None,
        on_gap: Callable[[str], None] | None = None,
        native_wait_seconds: float = 2.0,
        error_directory: Path | None = None,
        budget: RollingStreamBudget | None = None,
    ) -> None:
        self.adapter = AlchemyTransactionEvidenceStream(token, max_bytes=max_bytes, budget=budget)
        self.buffer = EvidenceBuffer(max_events=1024, per_market=128, max_bytes=16_000_000)
        self.watch = EarlyWatch(8)
        self.metrics: Counter[str] = Counter()
        self.logger = get_logger("memebot.executed_evidence")
        self.closed = False
        self.stream_stopped = False
        self.process_packet = process_packet
        self.on_gap = on_gap
        self.queue: asyncio.Queue[tuple[TransactionEvidence, int]] = asyncio.Queue(maxsize=128)
        self.queued_bytes = 0
        self.native_wait_seconds = native_wait_seconds
        self.status = "STARTING"
        self.error_directory = error_directory
        self.process_native: Callable[[dict[str, object], datetime], Awaitable[None]] | None = None
        self.pending_native: OrderedDict[
            str, tuple[dict[str, object], datetime, str, float, int]
        ] = OrderedDict()
        self.pending_native_bytes = 0
        self.adapter.on_control = self._control

    def _control(self, event: dict[str, Any]) -> None:
        if (
            event.get("kind") == "ack"
            and event.get("revision", -1) >= self.adapter.revision
            and self.adapter.accounts
            and self.status not in {"BUDGET_EXHAUSTED", "STOPPED"}
        ):
            # Subscription readiness is not COMPLETE_FOR_WINDOW. It only permits
            # the bounded native/full arbitration before the first full packet.
            self.status = "STREAMING"

    def defer_native(self, message: dict[str, object], received_at: datetime, mint: str) -> bool:
        if (
            mint not in self.watch.markets
            or self.process_native is None
            or self.status != "STREAMING"
        ):
            return False
        result: Any = message["params"]
        signature = str(result["result"]["value"]["signature"])
        if signature in self.pending_native:
            return True
        size = len(json.dumps(message).encode())
        if len(self.pending_native) >= 128 or self.pending_native_bytes + size > 4_000_000:
            self.metrics["native_wait_overflow"] += 1
            if self.on_gap is not None:
                self.on_gap("NATIVE_EVIDENCE_WAIT_OVERFLOW")
            return False
        self.pending_native[signature] = (message, received_at, mint, monotonic(), size)
        self.pending_native_bytes += size
        self.metrics["native_deferred"] += 1
        return True

    def _remove_native(self, signature: str) -> None:
        pending = self.pending_native.pop(signature, None)
        if pending is not None:
            self.pending_native_bytes -= pending[4]

    async def _flush_native(self) -> None:
        for signature, (message, received, mint, started, _) in list(self.pending_native.items()):
            if monotonic() - started < self.native_wait_seconds:
                continue
            # A queued full packet wins; original receipt times are preserved.
            if self.buffer.get(signature, utc_now()) is not None and not self.queue.empty():
                continue
            self._remove_native(signature)
            if mint in self.watch.markets and self.process_native is not None:
                self.metrics["native_wait_expired"] += 1
                try:
                    await self.process_native(message, received)
                except Exception as error:
                    self.metrics["native_failures"] += 1
                    if self.on_gap is not None:
                        self.on_gap("DEFERRED_NATIVE_FAILURE")
                    self._record_failure("deferred_native", error, signature, message)

    def _record_failure(
        self, source: str, error: Exception, signature: str, packet: dict[str, Any]
    ) -> None:
        frames = [
            {"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
            for f in traceback.extract_tb(error.__traceback__)[-8:]
        ]
        # Validation inputs and messages can contain arbitrary payloads. Only
        # field locations and machine-readable types are safe diagnostics.
        fields = (
            [{"loc": e["loc"], "type": e["type"]} for e in error.errors()]
            if isinstance(error, ValidationError)
            else []
        )
        details = dict(error_code=type(error).__name__, frames=frames, fields=fields)
        self.logger.error(f"{source}_failed", signature=signature, **details)
        count = self.metrics["native_failures"] + self.metrics["processor_failures"]
        if self.error_directory is not None and count <= 5:
            try:
                self.error_directory.mkdir(parents=True, exist_ok=True)
                payload = json.dumps({"transaction": packet, **details}, default=str)
                if len(payload.encode()) <= 4_000_000:
                    path = self.error_directory / f"packet-{count}.json"
                    path.write_text(payload, encoding="utf-8")
            except OSError:
                self.logger.error("executed_error_retention_failed")

    def observe(self, event: DomainEvent) -> None:
        now = utc_now()
        if isinstance(event, TokenDiscovered):
            if (
                event.launch_venue == LaunchVenue.PUMP_FUN
                and event.is_mayhem_mode is False
                and event.quote_mint in {NATIVE_SOL_MINT, WRAPPED_SOL_MINT}
                and event.bonding_curve == curve_address(event.mint)
                and not event.entry_rejection_reason
            ):
                self.watch.admit(event.mint, now)
        elif isinstance(event, TokenTrade):
            if event.mint in self.watch.markets:
                self.metrics["watched_trades"] += 1
                self.metrics[f"watched_continuity_{event.normalized_state.continuity_status}"] += 1
            if (
                event.normalized_state.multi_event_ambiguous
                or event.normalized_state.is_mayhem_mode
            ):
                self.watch.remove(event.mint, "OUT_OF_SCOPE", now)
                self.buffer.exclude(event.mint)
            else:
                self.watch.touch(event.mint, now)
        elif isinstance(event, TokenLifecycleChanged) and event.lifecycle in {
            MarketLifecycle.GRADUATION,
            MarketLifecycle.POST_GRADUATION,
            MarketLifecycle.DEAD_OR_ILLIQUID,
        }:
            self.watch.remove(event.mint, "TERMINAL", now)
            self.buffer.exclude(event.mint)

    def lookup(self, signature: str, slot: int) -> dict[str, Any] | None:
        packet = self.buffer.get(signature, utc_now())
        if packet is None or packet.slot != slot or packet.mint not in self.watch.markets:
            self.metrics["cache_misses"] += 1
            return None
        self.metrics["cache_hits"] += 1
        return packet.transaction

    async def run(self) -> None:
        if self.adapter.budget is None:
            await self._run_once()
            return
        failures = 0
        while not self.closed:
            while not self.adapter.budget.can_receive():
                self.status = "BUDGET_EXHAUSTED"
                await asyncio.sleep(self.adapter.budget.retry_after_seconds())
            self.stream_stopped = False
            self.status = "CONNECTING"
            while not self.adapter.updates.empty():
                self.adapter.updates.get_nowait()
            self.adapter.accounts = ()
            self.adapter.update_filter(tuple(self.watch.accounts()))
            packets_before = self.adapter.metrics["full_packets"]
            await self._run_once()
            if self.status == "BUDGET_EXHAUSTED":
                continue
            # Healthy sessions don't consume the consecutive connection-failure
            # allowance for the rest of the worker's lifetime.
            failures = 1 if self.adapter.metrics["full_packets"] > packets_before else failures + 1
            if failures >= 3:
                return  # Bound unsuccessful provider retries; never reset spend.
            self.status = "RECONNECTING"
            self.metrics["reconnects"] += 1
            await asyncio.sleep(min(30, 2**failures))

    async def _run_once(self) -> None:
        # Cache fill is independent of the ordered native publisher; it performs
        # no database, RPC, normalization or strategy work.
        try:
            async for packet in self.adapter.transactions():
                self.status = "STREAMING"
                if isinstance(packet, TransactionEvidence) and packet.mint in self.watch.markets:
                    self.buffer.add(packet)
                    self.metrics["full_packets"] += 1
                    if self.process_packet is not None:
                        size = self.buffer.sizes.get(packet.signature, 0)
                        if self.queue.full() or self.queued_bytes + size > 4_000_000:
                            self.metrics["processor_overflow"] += 1
                            self.buffer.gap("EXECUTED_PROCESSOR_OVERFLOW")
                            if self.on_gap is not None:
                                self.on_gap("EXECUTED_PROCESSOR_OVERFLOW")
                            continue
                        self.queue.put_nowait((packet, size))
                        self.queued_bytes += size
                        self.metrics["queue_peak"] = max(
                            self.metrics["queue_peak"], self.queue.qsize()
                        )
            raise ConnectionError("full_stream_ended")
        except asyncio.CancelledError:
            self.status = "STOPPED"
            raise
        except FullStreamBudgetExceeded:
            self.status = "BUDGET_EXHAUSTED"
            self.buffer.gap("FULL_STREAM_BUDGET_EXHAUSTED")
            if self.on_gap is not None:
                self.on_gap("FULL_STREAM_BUDGET_EXHAUSTED")
            self.logger.warning(
                "executed_evidence_budget_exhausted",
                limit_bytes=(
                    self.adapter.budget.hourly_bytes
                    if self.adapter.budget is not None
                    else self.adapter.max_bytes
                ),
                budget_scope="rolling_hour" if self.adapter.budget is not None else "session",
            )
        except Exception as error:
            self.status = "UNAVAILABLE"
            self.buffer.gap("FULL_STREAM_FAILED")
            if self.on_gap is not None:
                self.on_gap("FULL_STREAM_FAILED")
            self.logger.warning("executed_evidence_unavailable", error_code=type(error).__name__)
        finally:
            self.stream_stopped = True
            self.buffer.items.clear()
            self.buffer.sizes.clear()
            self.buffer.total_bytes = 0
            self.logger.info(
                "executed_evidence_stopped",
                metrics=dict(self.metrics),
                transport=dict(self.adapter.metrics),
            )

    async def process(self) -> None:
        while True:
            try:
                await self._flush_native()
            except Exception as error:
                if self.on_gap is not None:
                    self.on_gap("DEFERRED_NATIVE_FAILURE")
                self.logger.error("deferred_native_failed", error_code=type(error).__name__)
            try:
                packet, size = await asyncio.wait_for(self.queue.get(), 0.05)
            except TimeoutError:
                continue
            self.queued_bytes -= size
            try:
                if packet.mint in self.watch.markets and self.process_packet is not None:
                    await self.process_packet(packet)
                    self.metrics["processed_packets"] += 1
                    self._remove_native(packet.signature)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.metrics["processor_failures"] += 1
                if self.on_gap is not None:
                    self.on_gap("EXECUTED_PROCESSOR_FAILURE")
                self._record_failure(
                    "executed_processor", error, packet.signature, packet.transaction
                )
            finally:
                self.queue.task_done()

    async def maintain(self) -> None:
        while not self.closed:
            self.watch.expire(utc_now())
            if not self.stream_stopped:
                self.adapter.update_filter(tuple(self.watch.accounts()))
            # Research helpers also keep lifetime diagnostic history. Bound it
            # for continuous operation; retain current watches and recent rows.
            for mapping in (self.watch.history, self.watch.stages):
                while len(mapping) > 1024:
                    victim = next(k for k in mapping if k not in self.watch.markets)
                    mapping.pop(victim)
            self.watch.transitions = self.watch.transitions[-1024:]
            self.watch.removals = self.watch.removals[-1024:]
            if len(self.watch.rejected) > 1024:
                self.watch.rejected.clear()
            if len(self.watch.capacity_missed) > 1024:
                self.watch.capacity_missed.clear()
            self.adapter.filter_history = self.adapter.filter_history[-128:]
            await asyncio.sleep(1)
