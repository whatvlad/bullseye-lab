from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import random
import re
from collections import Counter, OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol, cast
from uuid import UUID, uuid5

from pydantic import ValidationError
from websockets.asyncio.client import connect as websocket_connect

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.core.logging import get_logger
from memebot.eligibility import entry_rejection
from memebot.events.models import (
    ProviderConnectionState,
    ProviderHealthUpdated,
    TokenDiscovered,
    TokenLifecycleChanged,
    TokenTrade,
    TradeSide,
)
from memebot.market_state import InvalidationScope, MarketStateTracker
from memebot.models.market import LaunchVenue, MarketLifecycle, MarketValidationState
from memebot.providers.base import (
    CapabilityReport,
    MarketDataProvider,
    ProviderCapability,
    ProviderDescriptor,
    PublishEvent,
)
from memebot.providers.solana.base import RpcAccount, SolanaRpcProvider
from memebot.providers.solana.canonical import (
    config_addresses,
    curve_address,
    pool_address,
    pool_authority,
)
from memebot.providers.solana.encoding import BorshDecodeError
from memebot.providers.solana.invalidation import (
    irrelevant_standard_fee_read,
    scope_native_mutations,
)
from memebot.providers.solana.pump_idl import (
    PUMP_AMM_PROGRAM_ID,
    PUMP_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    WRAPPED_SOL_MINT,
    PumpAnchorEvent,
    PumpComplete,
    PumpCreate,
    PumpMayhemUpdate,
    PumpMigration,
    PumpSwapPoolCreated,
    PumpSwapTrade,
    PumpTrade,
    decode_anchor_event,
    decode_bonding_curve_account,
    decode_pool_account,
    decode_token_account,
)
from memebot.providers.solana.rpc import SolanaRpcError

_EVENT_NAMESPACE = UUID("ebf77b69-35f8-512f-bd20-3d737c528f77")
_INVOKE_RE = re.compile(r"^Program ([1-9A-HJ-NP-Za-km-z]+) invoke \[(\d+)]$")
_RETURN_RE = re.compile(r"^Program ([1-9A-HJ-NP-Za-km-z]+) (?:success|failed:)")
_PROGRAM_DATA_PREFIX = "Program data: "
_KNOWN_PROGRAMS = frozenset({PUMP_PROGRAM_ID, PUMP_AMM_PROGRAM_ID})


class WebSocketConnection(Protocol):
    def __aiter__(self) -> AsyncIterator[str | bytes]: ...

    async def send(self, message: str) -> None: ...

    async def close(self) -> None: ...


type ConnectFactory = Callable[..., AbstractAsyncContextManager[WebSocketConnection]]
type Sleep = Callable[[float], Awaitable[None]]


class StreamBufferOverflow(ConnectionError):
    """Loss of local receive coverage requires a fresh stream generation."""


class StreamIdleTimeout(ConnectionError):
    """No transport data arrived within the independent idle deadline."""


def deterministic_event_id(signature: str, source_sequence: int, kind: str) -> UUID:
    return uuid5(_EVENT_NAMESPACE, f"solana:{signature}:{source_sequence}:{kind}")


def extract_anchor_events(logs: list[str]) -> list[tuple[str, PumpAnchorEvent]]:
    """Extract known Anchor events while respecting the Solana invocation stack."""
    stack: list[str] = []
    decoded: list[tuple[str, PumpAnchorEvent]] = []
    for line in logs:
        invoked = _INVOKE_RE.match(line)
        if invoked:
            program_id, depth_text = invoked.groups()
            depth = int(depth_text)
            if depth <= len(stack):
                del stack[depth - 1 :]
            stack.append(program_id)
            continue

        returned = _RETURN_RE.match(line)
        if returned:
            program_id = returned.group(1)
            if program_id in stack:
                reverse_index = stack[::-1].index(program_id)
                del stack[len(stack) - reverse_index - 1 :]
            continue

        if not line.startswith(_PROGRAM_DATA_PREFIX) or not stack:
            continue
        program_id = stack[-1]
        if program_id not in _KNOWN_PROGRAMS:
            continue
        try:
            raw = base64.b64decode(line.removeprefix(_PROGRAM_DATA_PREFIX), validate=True)
            event = decode_anchor_event(program_id, raw)
        except (binascii.Error, BorshDecodeError, ValueError):
            continue
        if event is not None:
            decoded.append((program_id, event))
    return decoded


def unsupported_native_mutation(logs: list[str]) -> str | None:
    """Scope instruction/data inspection to the native program invocation stack."""
    stack: list[str] = []
    supported = {"Buy", "Sell", "BuyExactSolIn", "BuyExactQuoteIn"}
    for line in logs:
        invoked = _INVOKE_RE.match(line)
        returned = _RETURN_RE.match(line)
        if invoked:
            program, depth = invoked.groups()
            del stack[int(depth) - 1 :]
            stack.append(program)
        elif returned and returned.group(1) in stack:
            index = len(stack) - 1 - stack[::-1].index(returned.group(1))
            del stack[index:]
        elif stack and stack[-1] in _KNOWN_PROGRAMS:
            if (
                line.startswith("Program log: Instruction: ")
                and line.removeprefix("Program log: Instruction: ") not in supported
            ):
                return "unsupported_native_instruction"
            if line.startswith(_PROGRAM_DATA_PREFIX):
                try:
                    raw = base64.b64decode(line.removeprefix(_PROGRAM_DATA_PREFIX), validate=True)
                    if decode_anchor_event(stack[-1], raw) is None:
                        return "unsupported_native_event"
                except (binascii.Error, BorshDecodeError, ValueError):
                    return "native_event_decode_failure"
    if any("Log truncated" in line for line in logs):
        return "native_logs_truncated"
    return None


class PumpDiscoveryProvider(MarketDataProvider):
    """Read-only Pump/PumpSwap discovery over standard Solana JSON-RPC and WSS."""

    def __init__(
        self,
        settings: Settings,
        rpc: SolanaRpcProvider,
        *,
        connect_factory: ConnectFactory | None = None,
        sleep: Sleep = asyncio.sleep,
        jitter: Callable[[], float] = random.random,
        receive_queue_capacity: int = 8192,
    ) -> None:
        if receive_queue_capacity < 1:
            raise ValueError("receive_queue_capacity must be positive")
        self._receive_queue_capacity = receive_queue_capacity
        self._logger = get_logger("memebot.pump")
        self._receive_queue_depth = 0
        self._receive_queue_peak = 0
        self._queue_lag_ms = 0
        self._received_messages = 0
        self._processed_messages = 0
        self._receive_buffer_bytes = 0
        self._duplicate_messages = 0
        self._event_loop_lag_ms_peak = 0
        self._applied_notifications: OrderedDict[tuple[str, int, bytes], None] = OrderedDict()
        self.native_notification_router: (
            Callable[[dict[str, object], datetime, str], bool] | None
        ) = None
        self._settings = settings
        self._rpc = rpc
        self._connect_factory = connect_factory or cast(ConnectFactory, websocket_connect)
        self._sleep = sleep
        self._jitter = jitter
        self._closed = False
        self._connection: WebSocketConnection | None = None
        self._publish: PublishEvent | None = None
        self._reconnect_count = 0
        self._reconnect_streak = 0
        self._failed_notifications_skipped = 0
        self._initial_real_reserves: dict[str, int] = {}
        self._last_progress_bucket: dict[str, int] = {}
        self._bonding_curves: dict[str, str] = {}
        self._pump_swap_pools: dict[str, tuple[str, str]] = {}
        self._exit_watch_mints: set[str] = set()
        self._exit_pool_mints: dict[str, str] = {}
        self._exit_wakeup: Callable[[str, int | None, datetime], None] | None = None
        self.state_tracker = MarketStateTracker()
        self._last_health: tuple[ProviderConnectionState, str | None, bool, int | None] | None = (
            None
        )
        self._invalid_status_streak = 0
        # A synchronous cache lookup only: native ingestion never waits for a
        # second provider, transaction RPC, or an execution packet.
        self.transaction_evidence_lookup: Callable[[str, int], dict[str, Any] | None] | None = None
        self.native_instruction_metrics: Counter[str] = Counter()
        self.on_price_gap: Callable[[str | None], None] | None = None
        # Only the bounded executed watch set installs these locks. Other
        # discovery notifications keep their existing dispatch path.
        self.market_notification_locks: dict[str, asyncio.Lock] = {}

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name="solana_rpc_pump",
            requested_capabilities=frozenset(
                {
                    ProviderCapability.TOKEN_DISCOVERY,
                    ProviderCapability.MEME_LIFECYCLE,
                    ProviderCapability.TOKEN_TRADES,
                    ProviderCapability.RPC_ACCOUNTS,
                    ProviderCapability.RPC_LOGS,
                    ProviderCapability.RPC_TRANSACTIONS,
                }
            ),
        )

    async def probe_capabilities(self) -> CapabilityReport:
        health = await self._rpc.health()
        rpc_capabilities = frozenset(
            {
                ProviderCapability.RPC_ACCOUNTS,
                ProviderCapability.RPC_TRANSACTIONS,
            }
        )
        stream_capabilities = frozenset(
            {
                ProviderCapability.TOKEN_DISCOVERY,
                ProviderCapability.MEME_LIFECYCLE,
                ProviderCapability.TOKEN_TRADES,
                ProviderCapability.RPC_LOGS,
            }
        )
        if health.healthy:
            return CapabilityReport(
                provider=self.descriptor.name,
                checked_at=health.checked_at,
                confirmed=rpc_capabilities,
                unknown=stream_capabilities,
                notes=("WSS capabilities are confirmed only after subscriptions are accepted",),
            )
        return CapabilityReport(
            provider=self.descriptor.name,
            checked_at=health.checked_at,
            unavailable=rpc_capabilities,
            unknown=stream_capabilities,
            notes=(health.error or "RPC health check failed",),
        )

    def seed_bonding_curve(
        self,
        mint: str,
        bonding_curve: str,
        initial_real_reserves: int,
        *,
        progress_percent: Decimal | None = None,
    ) -> None:
        """Restore active curve identity after a worker restart."""
        self._bonding_curves[mint] = bonding_curve
        self._initial_real_reserves[mint] = initial_real_reserves
        self._last_progress_bucket[mint] = int(progress_percent or 0)

    def seed_pump_swap_pool(self, pool: str, mint: str, quote_mint: str) -> None:
        """Restore a validated PumpSwap pool after a worker restart."""
        self._pump_swap_pools[pool] = (mint, quote_mint)

    def seed_open_position(self, mint: str) -> None:
        self._exit_watch_mints.add(mint)
        self._exit_pool_mints[pool_address(0, pool_authority(mint), mint, WRAPPED_SOL_MINT)] = mint

    def set_exit_wakeup(self, callback: Callable[[str, int | None, datetime], None]) -> None:
        self._exit_wakeup = callback

    def _wake_received_positions(self, message: dict[str, object], received_at: datetime) -> None:
        if not self._exit_watch_mints or self._exit_wakeup is None:
            return
        try:
            result = cast(dict[str, object], cast(dict[str, object], message["params"])["result"])
            value = cast(dict[str, object], result["value"])
            slot = cast(dict[str, object], result["context"])["slot"]
            if value.get("err") is not None or not isinstance(slot, int):
                return
            logs = cast(list[str], value["logs"])
            mints = set()
            for _, event in extract_anchor_events(logs):
                mint = (
                    event.mint
                    if isinstance(event, PumpTrade)
                    else self._exit_pool_mints.get(event.pool)
                    if isinstance(event, PumpSwapTrade)
                    else None
                )
                if mint in self._exit_watch_mints:
                    mints.add(mint)
            for mint in mints:
                assert mint is not None
                self._exit_wakeup(mint, slot, received_at)
        except (KeyError, TypeError, ValueError, BorshDecodeError):
            # Receipt-only wake is an optimization; the ordered decoder remains authoritative.
            self._logger.warning("exit_receipt_wake_decode_failed")

    @property
    def receive_backlogged(self) -> bool:
        return self._receive_queue_depth > 0

    async def pin_open_position(self, mint: str) -> None:
        self.seed_open_position(mint)

    async def unpin_closed_position(self, mint: str) -> None:
        self._exit_watch_mints.discard(mint)
        self._exit_pool_mints.pop(
            pool_address(0, pool_authority(mint), mint, WRAPPED_SOL_MINT), None
        )

    async def run(self, publish: PublishEvent) -> None:
        self._publish = publish
        while not self._closed:
            retry_cooldown = 0.0
            try:
                async with self._connect_factory(
                    str(self._settings.solana_rpc_ws_url),
                    open_timeout=self._settings.solana_ws_open_timeout_seconds,
                    ping_interval=self._settings.solana_ws_ping_interval_seconds,
                    ping_timeout=self._settings.solana_ws_ping_timeout_seconds,
                    close_timeout=5,
                    max_queue=1024,
                ) as connection:
                    self._connection = connection
                    await self._consume(connection, publish)
                    if not self._closed:
                        raise ConnectionError("websocket_stream_ended")
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if self._closed:
                    break
                if self._connection is not None:
                    self.state_tracker.invalidate(
                        None,
                        "STREAM_DISCONNECT",
                        scope_reason="shared_websocket_receive_interrupted",
                    )
                self._reconnect_count += 1
                self._reconnect_streak += 1
                error_code = type(error).__name__[:64]
                self._logger.warning(
                    "websocket_disconnect",
                    error_code=error_code,
                    **self._close_diagnostics(error),
                    queue_depth=self._receive_queue_depth,
                    queue_peak=self._receive_queue_peak,
                    queue_lag_ms=self._queue_lag_ms,
                    received_messages=self._received_messages,
                    processed_messages=self._processed_messages,
                    duplicate_messages=self._duplicate_messages,
                    queue_bytes=self._receive_buffer_bytes,
                )
                http_status = getattr(getattr(error, "response", None), "status_code", None)
                if not isinstance(http_status, int) or not 100 <= http_status <= 599:
                    http_status = None
                if http_status in {401, 403}:
                    retry_cooldown = self._settings.solana_halted_probe_seconds
                elif http_status == 429:
                    from memebot.providers.solana.rpc import _retry_after_seconds

                    headers = getattr(getattr(error, "response", None), "headers", {})
                    retry_cooldown = max(30, _retry_after_seconds(headers.get("Retry-After")))
                if error_code == "InvalidStatus":
                    self._invalid_status_streak += 1
                else:
                    self._invalid_status_streak = 0
                halted = (
                    self._invalid_status_streak
                    >= self._settings.solana_invalid_status_halt_threshold
                )
                await self._publish_health(
                    ProviderConnectionState.DEGRADED,
                    error_code="rpc_service_halted" if halted else error_code,
                    rate_limited=http_status == 429,
                    http_status=http_status,
                )
            finally:
                self._connection = None

            if not self._closed:
                if (
                    self._invalid_status_streak
                    >= self._settings.solana_invalid_status_halt_threshold
                ):
                    delay = self._settings.solana_halted_probe_seconds
                else:
                    exponential = self._settings.solana_reconnect_base_seconds * (
                        2 ** min(max(self._reconnect_streak - 1, 0), 10)
                    )
                    delay = min(exponential, self._settings.solana_reconnect_max_seconds)
                    delay += self._jitter() * self._settings.solana_reconnect_jitter_seconds
                delay = max(delay, retry_cooldown)
                await self._sleep(delay)

        await self._publish_health(ProviderConnectionState.DISCONNECTED)

    async def _consume(self, connection: WebSocketConnection, publish: PublishEvent) -> None:
        # Keep draining the transport while ordered downstream work awaits RPC/DB.
        # Never block the socket on a full application buffer: fail explicitly,
        # invalidate continuity in run(), and cancel the old generation instead.
        queue: asyncio.Queue[tuple[str | bytes, datetime] | None] = asyncio.Queue(
            maxsize=self._receive_queue_capacity
        )
        self._receive_queue_depth = self._receive_queue_peak = 0
        self._queue_lag_ms = self._received_messages = self._processed_messages = 0
        self._receive_buffer_bytes = 0
        self._duplicate_messages = 0
        seen: OrderedDict[tuple[str, int, bytes], None] = OrderedDict()
        last_receive = asyncio.get_running_loop().time()

        async def receive() -> None:
            nonlocal last_receive
            async for raw in connection:
                if self._closed:
                    break
                received_at = utc_now()
                last_receive = asyncio.get_running_loop().time()
                # Pump and fee-program subscriptions overlap. Only identical
                # successful transaction logs are duplicates; changed/truncated
                # evidence, other slots and malformed messages still pass through.
                message = self._parse_message(raw)
                if self._failed_transaction_notification(message):
                    # Failed transactions never enter the downstream decoder.
                    # Discard them before they consume the bounded queue used by
                    # successful market updates; control messages still pass.
                    self._failed_notifications_skipped += 1
                    await asyncio.sleep(0)
                    continue
                key = self._notification_key(message)
                if key is not None:
                    if key in seen:
                        self._duplicate_messages += 1
                        await asyncio.sleep(0)
                        continue
                    seen[key] = None
                    if len(seen) > 4096:
                        seen.popitem(last=False)
                    self._wake_received_positions(message, received_at)
                size = len(raw) if isinstance(raw, bytes) else len(raw.encode("utf-8"))
                if self._receive_buffer_bytes + size > 16 * 1024 * 1024:
                    raise StreamBufferOverflow("native_receive_byte_limit")
                try:
                    queue.put_nowait((raw, received_at))
                except asyncio.QueueFull as error:
                    raise StreamBufferOverflow("native_receive_buffer_full") from error
                self._received_messages += 1
                self._receive_buffer_bytes += size
                self._receive_queue_depth = queue.qsize()
                self._receive_queue_peak = max(self._receive_queue_peak, queue.qsize())
                # Fairness also covers test transports and bursts already buffered.
                await asyncio.sleep(0)
            await queue.put(None)

        async def measure_loop_lag() -> None:
            loop = asyncio.get_running_loop()
            interval = min(1.0, self._settings.solana_ws_idle_timeout_seconds / 2)
            while True:
                deadline = loop.time() + interval
                await asyncio.sleep(interval)
                self._event_loop_lag_ms_peak = max(
                    self._event_loop_lag_ms_peak, int(max(0, loop.time() - deadline) * 1000)
                )
                if loop.time() - last_receive >= self._settings.solana_ws_idle_timeout_seconds:
                    raise StreamIdleTimeout("native_stream_idle")

        async def messages() -> AsyncIterator[tuple[str | bytes, datetime]]:
            while True:
                item = await queue.get()
                self._receive_queue_depth = queue.qsize()
                if item is None:
                    return
                raw = item[0]
                self._receive_buffer_bytes -= (
                    len(raw) if isinstance(raw, bytes) else len(raw.encode("utf-8"))
                )
                self._queue_lag_ms = max(0, int((utc_now() - item[1]).total_seconds() * 1000))
                yield item
                self._processed_messages += 1
                if self._processed_messages % 1000 == 0:
                    self._logger.info(
                        "websocket_receive_progress",
                        queue_depth=queue.qsize(),
                        queue_peak=self._receive_queue_peak,
                        queue_lag_ms=self._queue_lag_ms,
                        received_messages=self._received_messages,
                        processed_messages=self._processed_messages,
                        duplicate_messages=self._duplicate_messages,
                        failed_notifications_skipped=self._failed_notifications_skipped,
                        queue_bytes=self._receive_buffer_bytes,
                        event_loop_lag_ms_peak=self._event_loop_lag_ms_peak,
                        websocket_latency_ms=int(float(getattr(connection, "latency", 0)) * 1000),
                    )
                if self._closed:
                    return

        receiver = asyncio.create_task(receive(), name="pump-socket-receive")
        lag_monitor = asyncio.create_task(measure_loop_lag(), name="pump-loop-lag")
        processor = asyncio.create_task(
            self._process_messages(connection, messages(), publish), name="pump-event-process"
        )
        try:
            done, _ = await asyncio.wait(
                (receiver, processor, lag_monitor), return_when=asyncio.FIRST_COMPLETED
            )
            if lag_monitor in done:
                await lag_monitor
            if receiver in done:
                await receiver  # A disconnect/overflow cancels pending old events.
                await processor  # A clean iterator end drains already received events.
            else:
                await processor
        finally:
            receiver.cancel()
            processor.cancel()
            lag_monitor.cancel()
            await asyncio.gather(receiver, processor, lag_monitor, return_exceptions=True)

    @staticmethod
    def _failed_transaction_notification(message: dict[str, object]) -> bool:
        if message.get("method") != "logsNotification":
            return False
        try:
            params = cast(dict[str, object], message["params"])
            result = cast(dict[str, object], params["result"])
            value = cast(dict[str, object], result["value"])
            return value.get("err") is not None
        except (KeyError, TypeError, AttributeError):
            return False

    @staticmethod
    def _notification_key(message: dict[str, object]) -> tuple[str, int, bytes] | None:
        if message.get("method") != "logsNotification":
            return None
        try:
            result = cast(dict[str, object], cast(dict[str, object], message["params"])["result"])
            value = cast(dict[str, object], result["value"])
            slot = cast(dict[str, object], result["context"])["slot"]
            signature, logs = value["signature"], value["logs"]
            if (
                value.get("err") is None
                and isinstance(signature, str)
                and isinstance(slot, int)
                and isinstance(logs, list)
                and all(isinstance(line, str) for line in logs)
            ):
                return signature, slot, hashlib.sha256(json.dumps(logs).encode()).digest()
        except (KeyError, TypeError):
            pass
        return None

    @staticmethod
    def _close_diagnostics(error: Exception) -> dict[str, object]:
        # Remote reasons and exception text can contain arbitrary data/credentials.
        # Retain only numeric codes and a known heartbeat reason classification.
        received = getattr(error, "rcvd", None)
        sent = getattr(error, "sent", None)
        reason = getattr(sent, "reason", "")
        return {
            "received_close_code": getattr(received, "code", None),
            "sent_close_code": getattr(sent, "code", None),
            "close_reason": "keepalive_ping_timeout"
            if reason == "keepalive ping timeout"
            else "remote_close"
            if received is not None
            else "no_remote_close_frame",
        }

    async def _process_messages(
        self,
        connection: WebSocketConnection,
        messages: AsyncIterator[tuple[str | bytes, datetime]],
        publish: PublishEvent,
    ) -> None:
        # Fee-program logs include every PumpSwap fee read. Watch the canonical
        # Pump fee configuration account directly instead of this global firehose.
        requests = {
            1: (
                "logsSubscribe",
                [{"mentions": [PUMP_PROGRAM_ID]}, {"commitment": self._settings.solana_commitment}],
            ),
            2: (
                "accountSubscribe",
                [
                    config_addresses()["pump_fee"][0],
                    {"encoding": "base64", "commitment": self._settings.solana_commitment},
                ],
            ),
        }
        fee_subscription: int | None = None
        for request_id, (method, params) in requests.items():
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
            await connection.send(json.dumps(request, separators=(",", ":")))

        accepted: set[int] = set()
        connected_published = False
        async for raw_message, received_at in messages:
            message = self._parse_message(raw_message)
            response_id = message.get("id")
            if isinstance(response_id, int) and response_id in requests:
                if "error" in message or not isinstance(message.get("result"), int):
                    raise RuntimeError("logs_subscription_rejected")
                accepted.add(response_id)
                if response_id == 2:
                    fee_subscription = cast(int, message["result"])
                if len(accepted) == len(requests) and not connected_published:
                    connected_published = True
                    self._reconnect_streak = 0
                    self._invalid_status_streak = 0
                    await self._publish_health(ProviderConnectionState.CONNECTED)
                continue
            if message.get("method") == "accountNotification":
                params = cast(dict[str, Any], message.get("params", {}))
                if fee_subscription is not None and params.get("subscription") == fee_subscription:
                    result = params.get("result", {})
                    slot = result.get("context", {}).get("slot")
                    self.state_tracker.invalidate(
                        None,
                        "CONFIG_CHANGE",
                        program=PUMP_PROGRAM_ID,
                        slot=slot if isinstance(slot, int) else None,
                        dimensions=("config",),
                        scope_reason="canonical_pump_fee_account_update",
                    )
                    self.native_instruction_metrics["PUMP_FEE_ACCOUNT_CHANGED"] += 1
                continue
            if message.get("method") == "logsNotification":
                processing_started = asyncio.get_running_loop().time()
                try:
                    await self._handle_notification(message, publish, received_at=received_at)
                except ValidationError as error:
                    # Bad decoded/event values are a data gap, not a broken
                    # socket. Invalidate continuity and retain safe field names;
                    # never print provider payloads or claim the sample valid.
                    self.state_tracker.invalidate(None, "INVALID_NATIVE_EVENT")
                    if self.on_price_gap is not None:
                        self.on_price_gap(None)
                    self._logger.error(
                        "native_event_validation_failed",
                        errors=[
                            {"field": ".".join(map(str, item["loc"])), "type": item["type"]}
                            for item in error.errors(include_input=False, include_url=False)
                        ],
                    )
                processing_ms = int((asyncio.get_running_loop().time() - processing_started) * 1000)
                if processing_ms >= 500:
                    self._logger.warning(
                        "websocket_slow_processing",
                        processing_ms=processing_ms,
                        queue_depth=self._receive_queue_depth,
                        queue_bytes=self._receive_buffer_bytes,
                    )
            if self._closed:
                break

    @staticmethod
    def _parse_message(raw_message: str | bytes) -> dict[str, object]:
        try:
            decoded = json.loads(raw_message)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError("invalid_ws_json") from error
        if not isinstance(decoded, dict):
            raise RuntimeError("invalid_ws_message")
        return cast(dict[str, object], decoded)

    async def _handle_notification(
        self,
        message: dict[str, object],
        publish: PublishEvent,
        *,
        received_at: datetime | None = None,
        transaction_evidence: dict[str, Any] | None = None,
        allow_defer: bool = True,
    ) -> None:
        try:
            params = cast(dict[str, object], message["params"])
            result = cast(dict[str, object], params["result"])
            context = cast(dict[str, object], result["context"])
            value = cast(dict[str, object], result["value"])
            signature = value["signature"]
            logs = value["logs"]
            slot = context["slot"]
        except (KeyError, TypeError):
            return
        if value.get("err") is not None:
            return
        if not (
            isinstance(signature, str)
            and 32 <= len(signature) <= 128
            and isinstance(slot, int)
            and isinstance(logs, list)
            and all(isinstance(line, str) for line in logs)
        ):
            return

        received_at = received_at or utc_now()
        if not self._exit_watch_mints and irrelevant_standard_fee_read(logs):
            self.native_instruction_metrics["EXCLUDED_VENUE_FEE_READ"] += 1
            return
        key = (signature, slot, hashlib.sha256(json.dumps(logs).encode()).digest())
        if key in self._applied_notifications:
            self.native_instruction_metrics["DUPLICATE_ALREADY_APPLIED"] += 1
            return
        events = extract_anchor_events(logs)
        trades = [e for _, e in events if isinstance(e, PumpTrade)]
        if (
            transaction_evidence is None
            and allow_defer
            and len(trades) == 1
            and self.native_notification_router is not None
            and self.native_notification_router(message, received_at, trades[0].mint)
        ):
            return
        lock = self.market_notification_locks.get(trades[0].mint) if len(trades) == 1 else None
        if lock is not None:
            async with lock:
                await self._apply_notification(
                    logs, events, signature, slot, received_at, publish, transaction_evidence
                )
        else:
            await self._apply_notification(
                logs, events, signature, slot, received_at, publish, transaction_evidence
            )

    async def _apply_notification(
        self,
        logs: list[str],
        events: list[tuple[str, PumpAnchorEvent]],
        signature: str,
        slot: int,
        received_at: datetime,
        publish: PublishEvent,
        transaction_evidence: dict[str, Any] | None,
    ) -> None:
        key = (signature, slot, hashlib.sha256(json.dumps(logs).encode()).digest())
        if key in self._applied_notifications:
            self.native_instruction_metrics["DUPLICATE_ALREADY_APPLIED"] += 1
            return
        # Unknown native instruction logs and non-trade events cannot establish
        # complete mutation coverage. Conservatively invalidate cached history.
        transaction = transaction_evidence or (
            self.transaction_evidence_lookup(signature, slot)
            if self.transaction_evidence_lookup is not None
            else None
        )
        scope_native_mutations(
            logs,
            self.state_tracker,
            signature=signature,
            slot=slot,
            transaction=transaction,
            classification_counts=self.native_instruction_metrics,
        )
        for ordinal, (_program_id, anchor_event) in enumerate(events):
            await self._normalize_and_publish(
                anchor_event,
                signature=signature,
                slot=slot,
                ordinal=ordinal,
                received_at=received_at,
                publish=publish,
                multi_event_unknown=isinstance(anchor_event, PumpTrade)
                and sum(isinstance(e, PumpTrade) for _, e in events) > 1,
            )
        # Remember only successfully applied notifications. A failed projection
        # may be retried; different log bytes still go through the safety guard.
        if transaction_evidence is not None or any(
            isinstance(event, PumpCreate)
            or (isinstance(event, PumpTrade) and event.mint in self._bonding_curves)
            for _, event in events
        ):
            self._applied_notifications[key] = None
            if len(self._applied_notifications) > 8192:
                self._applied_notifications.popitem(last=False)

    async def _normalize_and_publish(
        self,
        anchor_event: PumpAnchorEvent,
        *,
        signature: str,
        slot: int,
        ordinal: int,
        received_at: datetime,
        publish: PublishEvent,
        multi_event_unknown: bool = False,
    ) -> None:
        source_at = self._source_time(anchor_event.timestamp, received_at)
        base_sequence = ordinal * 10
        common = {
            "provider": self.descriptor.name,
            "source_event_at": source_at,
            "source_timestamp_estimated": source_at == received_at,
            "provider_received_at": received_at,
            "source_signature": signature,
            "source_slot": slot,
        }

        if isinstance(anchor_event, PumpCreate):
            self._initial_real_reserves[anchor_event.mint] = anchor_event.real_token_reserves
            self._last_progress_bucket[anchor_event.mint] = 0
            self._bonding_curves[anchor_event.mint] = anchor_event.bonding_curve
            await publish(
                TokenDiscovered(
                    **common,
                    event_id=deterministic_event_id(signature, base_sequence, "pump_create"),
                    source_sequence=base_sequence,
                    mint=anchor_event.mint,
                    name=anchor_event.name,
                    symbol=anchor_event.symbol,
                    creator=anchor_event.creator,
                    launch_venue=LaunchVenue.PUMP_FUN,
                    bonding_curve=anchor_event.bonding_curve,
                    quote_mint=anchor_event.quote_mint,
                    metadata_uri=anchor_event.uri,
                    initial_real_token_reserves=anchor_event.real_token_reserves,
                    token_total_supply=anchor_event.token_total_supply,
                    is_mayhem_mode=anchor_event.is_mayhem_mode,
                    entry_rejection_reason="OUT_OF_SCOPE_MAYHEM"
                    if anchor_event.is_mayhem_mode
                    else None,
                )
            )
            # The event was emitted by the pinned canonical Pump program and
            # already contains the curve, creator and quote identities. Avoid a
            # getAccount call for every newly created token; candidate risk checks
            # and the position monitor still refresh accounts on demand.
            await publish(
                TokenLifecycleChanged(
                    **common,
                    event_id=deterministic_event_id(
                        signature, base_sequence + 1, "pump_curve_validated"
                    ),
                    source_sequence=base_sequence + 1,
                    mint=anchor_event.mint,
                    lifecycle=MarketLifecycle.BONDING_CURVE,
                    validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
                    bonding_progress_percent=Decimal("0"),
                    market=anchor_event.bonding_curve,
                    quote_mint=anchor_event.quote_mint,
                    real_token_reserves=anchor_event.real_token_reserves,
                    reason="canonical_program_event",
                    is_mayhem_mode=anchor_event.is_mayhem_mode,
                    entry_rejection_reason="OUT_OF_SCOPE_MAYHEM"
                    if anchor_event.is_mayhem_mode
                    else None,
                )
            )
            return

        if isinstance(anchor_event, PumpMayhemUpdate):
            self.state_tracker.apply_mayhem_update(
                anchor_event,
                market=self._bonding_curves.get(anchor_event.mint)
                or curve_address(anchor_event.mint),
                signature=signature,
                slot=slot,
                ordinal=ordinal,
            )
            return

        if isinstance(anchor_event, PumpTrade):
            market = self._bonding_curves.get(anchor_event.mint)
            if market is None:
                return
            if anchor_event.token_amount <= 0 or anchor_event.quote_amount <= 0:
                # A zero-value event cannot produce a positive executable trade.
                # Retain a scoped continuity gap instead of letting the domain
                # validator turn one token's bad sample into a venue-wide reset.
                self.state_tracker.invalidate(
                    market,
                    "INVALID_NATIVE_EVENT",
                    signature=signature,
                    slot=slot,
                    dimensions=("reserves",),
                    scope_reason="non_positive_trade_amount",
                )
                if self.on_price_gap is not None:
                    self.on_price_gap(anchor_event.mint)
                self.native_instruction_metrics["NON_POSITIVE_TRADE_AMOUNT"] += 1
                self._logger.warning(
                    "native_trade_amount_rejected",
                    mint=anchor_event.mint,
                    signature=signature,
                    slot=slot,
                    reason="non_positive_trade_amount",
                )
                return
            normalized = self.state_tracker.observe(
                anchor_event,
                market=market,
                slot=slot,
                signature=signature,
                ordinal=ordinal,
                multi_event_unknown=multi_event_unknown,
            )
            if anchor_event.is_mayhem_mode:
                # Retain mutation/identity evidence, but never run the global
                # excluded Mayhem trade flow through durable strategy processing.
                # Discovery already records OUT_OF_SCOPE_MAYHEM.
                return
            await publish(
                TokenTrade(
                    **common,
                    event_id=deterministic_event_id(signature, base_sequence, "pump_trade"),
                    source_sequence=base_sequence,
                    mint=anchor_event.mint,
                    signature=signature,
                    side=TradeSide.BUY if anchor_event.is_buy else TradeSide.SELL,
                    token_amount=Decimal(anchor_event.token_amount),
                    quote_amount=Decimal(anchor_event.quote_amount),
                    quote_asset=anchor_event.quote_mint,
                    quote_mint=anchor_event.quote_mint,
                    wallet=anchor_event.user,
                    market=market,
                    real_token_reserves=normalized.token_reserve,
                    real_quote_reserves=normalized.quote_reserve,
                    virtual_token_reserves=normalized.virtual_token,
                    virtual_quote_reserves=normalized.virtual_quote,
                    normalized_state=normalized,
                    entry_rejection_reason=entry_rejection(normalized.evidence()),
                )
            )
            initial_reserves = self._initial_real_reserves.get(anchor_event.mint)
            if normalized.observational_price is None:
                return
            if initial_reserves:
                remaining = min(anchor_event.real_token_reserves, initial_reserves)
                progress = Decimal(initial_reserves - remaining) * 100 / Decimal(initial_reserves)
                progress_bucket = int(progress)
                if progress_bucket <= self._last_progress_bucket.get(anchor_event.mint, -1):
                    return
                self._last_progress_bucket[anchor_event.mint] = progress_bucket
                lifecycle = (
                    MarketLifecycle.FINAL_STRETCH
                    if progress >= self._settings.pump_final_stretch_percent
                    else MarketLifecycle.BONDING_CURVE
                )
                await publish(
                    TokenLifecycleChanged(
                        **common,
                        event_id=deterministic_event_id(
                            signature, base_sequence + 1, "pump_trade_lifecycle"
                        ),
                        source_sequence=base_sequence + 1,
                        mint=anchor_event.mint,
                        lifecycle=lifecycle,
                        validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
                        bonding_progress_percent=progress,
                        market=market,
                        quote_mint=anchor_event.quote_mint,
                        real_token_reserves=anchor_event.real_token_reserves,
                        real_quote_reserves=anchor_event.real_quote_reserves,
                        is_mayhem_mode=anchor_event.is_mayhem_mode,
                        entry_rejection_reason="OUT_OF_SCOPE_MAYHEM"
                        if anchor_event.is_mayhem_mode
                        else None,
                    )
                )
            return

        if isinstance(anchor_event, PumpComplete):
            self.state_tracker.invalidate(anchor_event.bonding_curve, "graduation")
            self._bonding_curves[anchor_event.mint] = anchor_event.bonding_curve
            self._initial_real_reserves.pop(anchor_event.mint, None)
            self._last_progress_bucket.pop(anchor_event.mint, None)
            await publish(
                TokenLifecycleChanged(
                    **common,
                    event_id=deterministic_event_id(signature, base_sequence, "pump_complete"),
                    source_sequence=base_sequence,
                    mint=anchor_event.mint,
                    lifecycle=MarketLifecycle.GRADUATION,
                    validation_state=MarketValidationState.VERIFIED_MARKET_DATA,
                    bonding_progress_percent=Decimal("100"),
                    market=anchor_event.bonding_curve,
                    quote_mint=anchor_event.quote_mint,
                    entry_rejection_reason="MIGRATED_MARKET",
                )
            )
            return

        if isinstance(anchor_event, PumpMigration):
            self.state_tracker.invalidate(anchor_event.bonding_curve, "migration")
            self._initial_real_reserves.pop(anchor_event.mint, None)
            self._last_progress_bucket.pop(anchor_event.mint, None)
            self._pump_swap_pools[anchor_event.pool] = (
                anchor_event.mint,
                anchor_event.quote_mint,
            )
            validation, reason, reserves = MarketValidationState.REJECTED, "MIGRATED_MARKET", None
            await publish(
                TokenLifecycleChanged(
                    **common,
                    event_id=deterministic_event_id(signature, base_sequence, "pump_migration"),
                    source_sequence=base_sequence,
                    mint=anchor_event.mint,
                    lifecycle=MarketLifecycle.POST_GRADUATION,
                    validation_state=validation,
                    bonding_progress_percent=Decimal("100"),
                    market=anchor_event.pool,
                    quote_mint=anchor_event.quote_mint,
                    real_token_reserves=(reserves[0] if reserves else None),
                    real_quote_reserves=(reserves[1] if reserves else None),
                    reason=reason,
                    entry_rejection_reason=reason,
                )
            )
            return

        if isinstance(anchor_event, PumpSwapPoolCreated):
            self._pump_swap_pools[anchor_event.pool] = (
                anchor_event.base_mint,
                anchor_event.quote_mint,
            )
            await publish(
                TokenDiscovered(
                    **common,
                    event_id=deterministic_event_id(signature, base_sequence, "pump_swap_pool"),
                    source_sequence=base_sequence,
                    mint=anchor_event.base_mint,
                    creator=anchor_event.coin_creator,
                    launch_venue=LaunchVenue.PUMP_SWAP,
                    is_mayhem_mode=anchor_event.is_mayhem_mode,
                    entry_rejection_reason="OUT_OF_SCOPE_PUMPSWAP",
                    quote_mint=anchor_event.quote_mint,
                )
            )
            validation, reason, reserves = (
                MarketValidationState.REJECTED,
                "OUT_OF_SCOPE_PUMPSWAP",
                None,
            )
            await publish(
                TokenLifecycleChanged(
                    **common,
                    event_id=deterministic_event_id(
                        signature, base_sequence + 1, "pump_swap_pool_validated"
                    ),
                    source_sequence=base_sequence + 1,
                    mint=anchor_event.base_mint,
                    lifecycle=MarketLifecycle.POST_GRADUATION,
                    validation_state=validation,
                    bonding_progress_percent=Decimal("100") if anchor_event.index == 0 else None,
                    market=anchor_event.pool,
                    quote_mint=anchor_event.quote_mint,
                    real_token_reserves=(reserves[0] if reserves else None),
                    real_quote_reserves=(reserves[1] if reserves else None),
                    reason=reason,
                    entry_rejection_reason=reason,
                )
            )
            return

        if isinstance(anchor_event, PumpSwapTrade):
            identity = self._pump_swap_pools.get(anchor_event.pool)
            if identity is None:
                return
            mint, quote_mint = identity
            normalized = self.state_tracker.observe(
                anchor_event,
                market=anchor_event.pool,
                slot=slot,
                signature=signature,
                ordinal=ordinal,
            )
            if mint not in self._exit_watch_mints:
                # Excluded PumpSwap volume must not consume durable strategy or
                # wallet work. Retain mutation evidence and active exit watches.
                return
            await publish(
                TokenTrade(
                    **common,
                    event_id=deterministic_event_id(signature, base_sequence, "pump_swap_trade"),
                    source_sequence=base_sequence,
                    mint=mint,
                    signature=signature,
                    side=TradeSide.BUY if anchor_event.is_buy else TradeSide.SELL,
                    token_amount=Decimal(anchor_event.base_amount),
                    quote_amount=Decimal(anchor_event.quote_amount),
                    quote_asset=quote_mint,
                    quote_mint=quote_mint,
                    wallet=anchor_event.user,
                    market=anchor_event.pool,
                    real_token_reserves=normalized.token_reserve,
                    real_quote_reserves=normalized.quote_reserve,
                    virtual_quote_reserves=normalized.virtual_offset,
                    normalized_state=normalized,
                )
            )

    async def _validate_bonding_curve(
        self,
        address: str,
        creator: str,
        quote_mint: str,
    ) -> tuple[MarketValidationState, str | None, tuple[int, int] | None]:
        account = await self._get_account_with_retry(address)
        if account is None:
            return (
                MarketValidationState.INSUFFICIENT_DATA,
                "bonding_curve_account_unavailable",
                None,
            )
        if account.owner != PUMP_PROGRAM_ID:
            return MarketValidationState.REJECTED, "bonding_curve_owner_mismatch", None
        try:
            decoded = decode_bonding_curve_account(
                base64.b64decode(account.data_base64, validate=True)
            )
        except (binascii.Error, BorshDecodeError):
            return MarketValidationState.REJECTED, "bonding_curve_schema_mismatch", None
        if decoded.creator != creator or decoded.quote_mint != quote_mint:
            return MarketValidationState.REJECTED, "bonding_curve_identity_mismatch", None
        return (
            MarketValidationState.VERIFIED_MARKET_DATA,
            None,
            (decoded.real_token_reserves, decoded.real_quote_reserves),
        )

    async def _validate_pool(
        self,
        address: str,
        mint: str,
        quote_mint: str,
        *,
        canonical_only: bool,
    ) -> tuple[MarketValidationState, str | None, tuple[int, int] | None]:
        account = await self._get_account_with_retry(address)
        if account is None:
            return MarketValidationState.INSUFFICIENT_DATA, "pool_account_unavailable", None
        if account.owner != PUMP_AMM_PROGRAM_ID:
            return MarketValidationState.REJECTED, "pool_owner_mismatch", None
        try:
            decoded = decode_pool_account(base64.b64decode(account.data_base64, validate=True))
        except (binascii.Error, BorshDecodeError):
            return MarketValidationState.REJECTED, "pool_schema_mismatch", None
        if decoded.base_mint != mint or decoded.quote_mint != quote_mint:
            return MarketValidationState.REJECTED, "pool_identity_mismatch", None
        if canonical_only and decoded.index != 0:
            return MarketValidationState.REJECTED, "non_canonical_migration_pool", None
        base_account, quote_account = await asyncio.gather(
            self._get_account_with_retry(decoded.pool_base_token_account),
            self._get_account_with_retry(decoded.pool_quote_token_account),
        )
        if base_account is None or quote_account is None:
            return MarketValidationState.INSUFFICIENT_DATA, "pool_reserves_unavailable", None
        token_programs = {TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID}
        if base_account.owner not in token_programs or quote_account.owner not in token_programs:
            return MarketValidationState.REJECTED, "pool_token_account_owner_mismatch", None
        try:
            base_balance = decode_token_account(
                base64.b64decode(base_account.data_base64, validate=True)
            )
            quote_balance = decode_token_account(
                base64.b64decode(quote_account.data_base64, validate=True)
            )
        except (binascii.Error, BorshDecodeError):
            return MarketValidationState.REJECTED, "pool_reserve_schema_mismatch", None
        if base_balance.mint != mint or quote_balance.mint != quote_mint:
            return MarketValidationState.REJECTED, "pool_reserve_identity_mismatch", None
        effective_quote_reserves = quote_balance.amount + decoded.virtual_quote_reserves
        if base_balance.amount <= 0 or effective_quote_reserves <= 0:
            return MarketValidationState.INSUFFICIENT_DATA, "pool_has_no_liquidity", None
        return (
            MarketValidationState.VERIFIED_MARKET_DATA,
            None,
            (base_balance.amount, effective_quote_reserves),
        )

    async def _get_account_with_retry(self, address: str) -> RpcAccount | None:
        for attempt in range(self._settings.solana_account_retry_count):
            try:
                account = await self._rpc.get_account(
                    address,
                    self._settings.solana_commitment,
                )
            except Exception as error:
                account = None
                affected = {
                    key
                    for key, identity in self.state_tracker.identities.items()
                    if address
                    in {identity.market, identity.base_vault, identity.quote_vault, identity.curve}
                }
                self.state_tracker.invalidate(
                    address if not affected else None,
                    "RPC_RECONCILIATION_FAILURE",
                    affected_markets=affected if affected else None,
                    scope=InvalidationScope.MARKET
                    if len(affected) <= 1
                    else InvalidationScope.VENUE,
                    dimensions=("reserves",),
                    scope_reason="requested_account_identity_cache",
                )
                await self._publish_health(
                    ProviderConnectionState.DEGRADED,
                    error_code=type(error).__name__[:64],
                    rate_limited=(isinstance(error, SolanaRpcError) and error.rate_limited),
                )
            if account is not None:
                if self._last_health is not None and self._last_health[0] == (
                    ProviderConnectionState.DEGRADED
                ):
                    await self._publish_health(ProviderConnectionState.CONNECTED)
                return account
            if attempt + 1 < self._settings.solana_account_retry_count:
                await self._sleep(self._settings.solana_account_retry_delay_seconds)
        return None

    async def _publish_health(
        self,
        state: ProviderConnectionState,
        *,
        error_code: str | None = None,
        rate_limited: bool = False,
        http_status: int | None = None,
    ) -> None:
        if self._publish is None:
            return
        # Reconnect count is telemetry, not state identity. Excluding it prevents
        # identical outages from flooding the database and Telegram.
        health_key = (state, error_code, rate_limited, http_status)
        if health_key == self._last_health:
            return
        self._last_health = health_key
        connected = state == ProviderConnectionState.CONNECTED
        if state == ProviderConnectionState.DISCONNECTED:
            self.state_tracker.invalidate(
                None, "STREAM_DISCONNECT", scope_reason="shared_websocket_all_subscribed_programs"
            )
        capabilities = self.descriptor.requested_capabilities if connected else frozenset()
        unavailable = frozenset() if connected else self.descriptor.requested_capabilities
        await self._publish(
            ProviderHealthUpdated(
                provider=self.descriptor.name,
                source_event_at=utc_now(),
                state=state,
                confirmed_capabilities=frozenset(item.value for item in capabilities),
                unavailable_capabilities=frozenset(item.value for item in unavailable),
                reconnect_count=self._reconnect_count,
                rate_limited=rate_limited,
                http_status=http_status,
                error_code=error_code,
            )
        )

    @staticmethod
    def _source_time(timestamp: int, fallback: datetime) -> datetime:
        try:
            source = datetime.fromtimestamp(timestamp, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return fallback
        lower_bound = datetime(2020, 1, 1, tzinfo=UTC)
        if source < lower_bound or source > fallback + timedelta(days=1):
            return fallback
        return source

    async def close(self) -> None:
        self._closed = True
        if self._connection is not None:
            await self._connection.close()
        await self._publish_health(ProviderConnectionState.DISCONNECTED)
        await self._rpc.close()
