from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from time import monotonic
from typing import Any, Protocol, cast
from urllib.parse import quote

from websockets.asyncio.client import connect as websocket_connect

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.core.logging import get_logger
from memebot.events.models import (
    ProviderConnectionState,
    ProviderHealthUpdated,
    TokenDiscovered,
    TokenLifecycleChanged,
    TokenTrade,
    TradeSide,
)
from memebot.models.common import is_solana_address
from memebot.models.market import LaunchVenue, MarketLifecycle, MarketValidationState
from memebot.providers.base import (
    CapabilityReport,
    MarketDataProvider,
    ProviderCapability,
    ProviderDescriptor,
    PublishEvent,
)
from memebot.providers.curve_calibration import CurveCalibration
from memebot.providers.solana.pump import deterministic_event_id
from memebot.providers.solana.pump_idl import WRAPPED_SOL_MINT

_TOKEN_SCALE = Decimal(1_000_000)
_SOL_SCALE = Decimal(1_000_000_000)


class WebSocketConnection(Protocol):
    def __aiter__(self) -> AsyncIterator[str | bytes]: ...

    async def send(self, message: str) -> None: ...

    async def close(self) -> None: ...


type ConnectFactory = Callable[..., AbstractAsyncContextManager[WebSocketConnection]]
type Sleep = Callable[[float], Awaitable[None]]


class PumpPortalDiscoveryProvider(MarketDataProvider):
    """Budgeted PumpPortal discovery with short-lived token trade subscriptions."""

    def __init__(
        self,
        settings: Settings,
        *,
        connect_factory: ConnectFactory | None = None,
        sleep: Sleep = asyncio.sleep,
        jitter: Callable[[], float] = random.random,
        calibrate: Callable[[str, str, str | None], Awaitable[CurveCalibration | None]]
        | None = None,
    ) -> None:
        if settings.pumpportal_api_key is None:
            raise ValueError("pumpportal_api_key_required")
        self._settings = settings
        self._calibrate = calibrate
        self._calibrations: dict[str, CurveCalibration] = {}
        self._creation_context: dict[str, tuple[str, str | None]] = {}
        self._pools: dict[str, str] = {}
        self._research_until: dict[str, float] = {}
        self._candidate_queue: dict[str, tuple[Decimal, float]] = {}
        self._candidate_buyers: dict[str, set[str]] = {}
        self._candidate_flow: dict[str, Decimal] = {}
        self._api_key = settings.pumpportal_api_key.get_secret_value()
        self._logger = get_logger("memebot.pumpportal")
        self._connect_factory = connect_factory or cast(ConnectFactory, websocket_connect)
        self._sleep = sleep
        self._jitter = jitter
        self._closed = False
        self._connection: WebSocketConnection | None = None
        self._publish: PublishEvent | None = None
        self._reconnect_count = 0
        self._reconnect_streak = 0
        self._subscriptions: dict[str, float] = {}
        self._pinned_position_mints: set[str] = set()
        self._candidate_trade_counts: dict[str, int] = {}
        self._next_candidate_subscription_at = 0.0
        self._initial_virtual_tokens: dict[str, int] = {}
        self._last_progress_bucket: dict[str, int] = {}
        self._trade_budget_day: date = utc_now().date()
        self._trade_events_today = 0
        self._budget_halted = False
        self._next_budget_notice_at = 0.0
        self._last_health: tuple[ProviderConnectionState, str | None, int | None] | None = None

    def seed_daily_trade_usage(self, observed_day: date, event_count: int) -> None:
        """Restore usage telemetry; positive configured limits survive restarts."""
        today = utc_now().date()
        self._trade_budget_day = today
        self._trade_events_today = event_count if observed_day == today else 0
        self._budget_halted = (
            self._settings.pumpportal_max_trade_events_per_day > 0
            and self._trade_events_today >= self._settings.pumpportal_max_trade_events_per_day
        )

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name="pumpportal_budgeted",
            requested_capabilities=frozenset(
                {
                    ProviderCapability.TOKEN_DISCOVERY,
                    ProviderCapability.MEME_LIFECYCLE,
                    ProviderCapability.TOKEN_TRADES,
                }
            ),
        )

    async def probe_capabilities(self) -> CapabilityReport:
        return CapabilityReport(
            provider=self.descriptor.name,
            checked_at=utc_now(),
            unknown=self.descriptor.requested_capabilities,
            notes=("Entitlement is confirmed only after the WebSocket accepts subscriptions",),
        )

    def seed_bonding_curve(
        self,
        mint: str,
        bonding_curve: str,
        initial_real_reserves: int,
        *,
        progress_percent: Decimal | None = None,
    ) -> None:
        del progress_percent
        self._creation_context[mint] = (bonding_curve, None)
        if initial_real_reserves > 0:
            self._initial_virtual_tokens.setdefault(mint, initial_real_reserves)

    def seed_pump_swap_pool(self, pool: str, mint: str, quote_mint: str) -> None:
        if quote_mint == WRAPPED_SOL_MINT:
            self._pools[mint] = pool
            self._calibrations.pop(mint, None)

    def seed_open_position(self, mint: str) -> None:
        """Restore a durable live subscription before the socket is connected."""
        if is_solana_address(mint):
            self._pinned_position_mints.add(mint)
            self._subscriptions[mint] = float("inf")

    async def pin_open_position(self, mint: str) -> None:
        """Keep an opened position on the live trade stream until its full close."""
        if not is_solana_address(mint):
            return
        already_subscribed = mint in self._subscriptions
        self._pinned_position_mints.add(mint)
        self._subscriptions[mint] = float("inf")
        if self._connection is not None and not self._budget_halted and not already_subscribed:
            await self._send(self._connection, "subscribeTokenTrade", [mint])
        self._logger.info(
            "pumpportal_position_subscription_pinned",
            mint=mint,
            events_today=self._trade_events_today,
        )

    async def unpin_closed_position(self, mint: str) -> None:
        """Keep a bounded research lease after a full close."""
        self._pinned_position_mints.discard(mint)
        await self.observe_research(mint)
        return

    async def observe_research(self, mint: str, seconds: float | None = None) -> None:
        if not is_solana_address(mint):
            return
        self._reset_daily_budget_if_needed()
        limit = self._candidate_event_limit()
        if self._budget_halted or (limit is not None and self._trade_events_today >= limit):
            if mint not in self._pinned_position_mints:
                await self.release_subscription(mint)
            return
        duration = seconds if seconds is not None else self._settings.research_observation_seconds
        if duration <= 0:
            return
        if (
            mint not in self._research_until
            and len(self._research_until) >= self._settings.research_max_active_subscriptions
        ):
            oldest = min(self._research_until, key=self._research_until.__getitem__)
            self._research_until.pop(oldest)
            if oldest not in self._pinned_position_mints and self._connection is not None:
                await self._unsubscribe(
                    self._connection, oldest, reason="research_capacity_censored"
                )
        self._research_until[mint] = monotonic() + duration
        already = mint in self._subscriptions
        self._subscriptions[mint] = (
            float("inf") if mint in self._pinned_position_mints else self._research_until[mint]
        )
        if not already and self._connection is not None and not self._budget_halted:
            await self._send(self._connection, "subscribeTokenTrade", [mint])

    async def release_subscription(self, mint: str) -> None:
        if mint not in self._subscriptions:
            return
        if self._connection is not None:
            await self._unsubscribe(self._connection, mint, reason="position_closed")
        else:
            self._subscriptions.pop(mint, None)
            self._candidate_trade_counts.pop(mint, None)

    async def run(self, publish: PublishEvent) -> None:
        self._publish = publish
        while not self._closed:
            retry_cooldown = 0.0
            try:
                async with self._connect_factory(
                    self._endpoint(),
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
                self._reconnect_count += 1
                self._reconnect_streak += 1
                http_status = getattr(getattr(error, "response", None), "status_code", None)
                if not isinstance(http_status, int) or not 100 <= http_status <= 599:
                    http_status = None
                if http_status in {401, 403}:
                    retry_cooldown = self._settings.solana_halted_probe_seconds
                elif http_status == 429:
                    from memebot.providers.solana.rpc import _retry_after_seconds

                    headers = getattr(getattr(error, "response", None), "headers", {})
                    retry_cooldown = max(30, _retry_after_seconds(headers.get("Retry-After")))
                await self._publish_health(
                    ProviderConnectionState.DEGRADED,
                    error_code=type(error).__name__[:64],
                    http_status=http_status,
                )
            finally:
                self._connection = None

            if not self._closed:
                delay = min(
                    self._settings.solana_reconnect_base_seconds
                    * (2 ** min(max(self._reconnect_streak - 1, 0), 10)),
                    self._settings.solana_reconnect_max_seconds,
                )
                delay += self._jitter() * self._settings.solana_reconnect_jitter_seconds
                delay = max(delay, retry_cooldown)
                await self._sleep(delay)
        await self._publish_health(ProviderConnectionState.DISCONNECTED)

    async def _consume(self, connection: WebSocketConnection, publish: PublishEvent) -> None:
        await self._send(connection, "subscribeNewToken")
        await self._send(connection, "subscribeMigration")
        await self._expire_subscriptions(connection)
        for mint in tuple(self._subscriptions):
            await self._send(connection, "subscribeTokenTrade", [mint])
        self._reconnect_streak = 0
        if self._budget_halted:
            await self._publish_budget_halted()
        else:
            await self._publish_health(ProviderConnectionState.CONNECTED)

        async for raw_message in connection:
            await self._expire_subscriptions(connection)
            message = _parse_message(raw_message)
            if message is None:
                continue
            portal_error = _portal_error_code(message)
            if portal_error is not None:
                self._budget_halted = True
                self._subscriptions.clear()
                await self._publish_health(
                    ProviderConnectionState.DEGRADED,
                    error_code=portal_error,
                )
                continue
            if "message" in message:
                continue
            tx_type = str(message.get("txType", "")).lower()
            if tx_type == "create":
                await self._handle_create(message, connection, publish)
            elif tx_type in {"buy", "sell"}:
                await self._handle_trade(message, connection, publish)
            elif tx_type in {"migrate", "migration"} or message.get("poolMigration"):
                await self._handle_migration(message, publish)
            await self._drain_candidates(connection)
            if self._closed:
                break

    async def _handle_create(
        self,
        message: dict[str, Any],
        connection: WebSocketConnection,
        publish: PublishEvent,
    ) -> None:
        mint = _address(message.get("mint"))
        curve = _address(message.get("bondingCurveKey"))
        signature = _signature(message.get("signature"))
        if mint is None or curve is None or signature is None:
            return
        received_at = utc_now()
        self._creation_context[mint] = (curve, signature)
        self._last_progress_bucket[mint] = 0
        common = _common(self.descriptor.name, signature, received_at)
        await publish(
            TokenDiscovered(
                **common,
                event_id=deterministic_event_id(signature, 0, "pumpportal_create"),
                source_sequence=0,
                mint=mint,
                name=_text(message.get("name"), 128),
                symbol=_text(message.get("symbol"), 32),
                creator=_address(message.get("traderPublicKey")),
                launch_venue=LaunchVenue.PUMP_FUN,
                bonding_curve=curve,
                quote_mint=WRAPPED_SOL_MINT,
                metadata_uri=_text(message.get("uri"), 1024),
                initial_real_token_reserves=None,
                token_total_supply=_raw_amount(message.get("tokenTotalSupply"), _TOKEN_SCALE),
            )
        )
        await publish(
            TokenLifecycleChanged(
                **common,
                event_id=deterministic_event_id(signature, 1, "pumpportal_curve"),
                source_sequence=1,
                mint=mint,
                lifecycle=MarketLifecycle.BONDING_CURVE,
                validation_state=MarketValidationState.INSUFFICIENT_DATA,
                bonding_progress_percent=Decimal(0),
                market=curve,
                quote_mint=WRAPPED_SOL_MINT,
                reason="third_party_stream_requires_rpc_candidate_validation",
            )
        )
        initial_buy = _raw_decimal(message.get("solAmount"), _SOL_SCALE) or Decimal(0)
        # Queue priority is discovery scheduling, never a probability of profit.
        priority = min(initial_buy, _SOL_SCALE) - max(Decimal(0), initial_buy - 3 * _SOL_SCALE)
        self._candidate_queue[mint] = (priority, monotonic())
        if len(self._candidate_queue) > 256:
            oldest = min(self._candidate_queue, key=lambda key: self._candidate_queue[key][1])
            self._candidate_queue.pop(oldest)
        await self._drain_candidates(connection)

    async def _drain_candidates(self, connection: WebSocketConnection) -> None:
        self._reset_daily_budget_if_needed()
        now = monotonic()
        self._candidate_queue = {
            mint: value for mint, value in self._candidate_queue.items() if now - value[1] <= 30
        }
        if not self._candidate_queue or now < self._next_candidate_subscription_at:
            return
        candidate_limit = self._candidate_event_limit()
        if candidate_limit is not None and self._trade_events_today >= candidate_limit:
            if now >= self._next_budget_notice_at:
                self._next_budget_notice_at = now + 300
                self._logger.warning(
                    "candidate_selection_paused_daily_budget",
                    events_today=self._trade_events_today,
                    candidate_limit=candidate_limit,
                    daily_limit=self._settings.pumpportal_max_trade_events_per_day,
                    resets_at_utc=datetime.combine(
                        self._trade_budget_day + timedelta(days=1), datetime.min.time(), tzinfo=UTC
                    ).isoformat(),
                    reason="discovery_continues_but_new_candidate_trades_are_not_subscribed",
                )
            return
        candidates = (
            set(self._subscriptions) - self._pinned_position_mints - set(self._research_until)
        )
        if len(candidates) >= self._settings.pumpportal_max_active_token_subscriptions:
            return
        mint = max(
            self._candidate_queue,
            key=lambda key: (self._candidate_queue[key][0], self._candidate_queue[key][1]),
        )
        self._candidate_queue.pop(mint)
        await self._subscribe_candidate(connection, mint)

    async def _handle_trade(
        self,
        message: dict[str, Any],
        connection: WebSocketConnection,
        publish: PublishEvent,
    ) -> None:
        self._reset_daily_budget_if_needed()
        mint = _address(message.get("mint"))
        if mint is None or mint not in self._subscriptions or self._budget_halted:
            return
        signature = _signature(message.get("signature"))
        token_amount = _raw_decimal(message.get("tokenAmount"), _TOKEN_SCALE)
        sol_amount = _raw_decimal(message.get("solAmount"), _SOL_SCALE)
        if signature is None or token_amount is None or sol_amount is None:
            return
        self._trade_events_today += 1
        if (
            self._settings.pumpportal_max_trade_events_per_day > 0
            and self._trade_events_today > self._settings.pumpportal_max_trade_events_per_day
        ):
            self._budget_halted = True
            await self._publish_budget_halted()
            return
        discretionary_limit = self._candidate_event_limit()
        if (
            discretionary_limit is not None
            and self._trade_events_today > discretionary_limit
            and mint not in self._pinned_position_mints
        ):
            self._research_until.pop(mint, None)
            await self._unsubscribe(connection, mint, reason="protected_position_budget")
            return
        self._candidate_trade_counts[mint] = self._candidate_trade_counts.get(mint, 0) + 1
        wallet = _address(message.get("traderPublicKey"))
        is_buy = str(message.get("txType", "")).lower() == "buy"
        if is_buy and wallet:
            self._candidate_buyers.setdefault(mint, set()).add(wallet)
        self._candidate_flow[mint] = self._candidate_flow.get(mint, Decimal(0)) + (
            sol_amount if is_buy else -sol_amount
        )
        if self._trade_events_today == 1 or self._trade_events_today % 100 == 0:
            self._logger.info(
                "pumpportal_trade_usage",
                events_today=self._trade_events_today,
                daily_limit=(self._settings.pumpportal_max_trade_events_per_day or "unlimited"),
                estimated_data_cost_sol=str(
                    (Decimal(self._trade_events_today) / Decimal(1_000_000)).quantize(
                        Decimal("0.000001")
                    )
                ),
                active_subscriptions=len(self._subscriptions),
            )
        received_at = utc_now()
        curve = _address(message.get("bondingCurveKey"))
        if mint in self._pools:
            curve = self._pools[mint]
        virtual_tokens = _raw_amount(message.get("vTokensInBondingCurve"), _TOKEN_SCALE)
        virtual_sol = _raw_amount(message.get("vSolInBondingCurve"), _SOL_SCALE)
        calibration = self._calibrations.get(mint)
        real_tokens = (
            max(0, virtual_tokens - calibration.token_offset)
            if calibration and virtual_tokens is not None
            else None
        )
        real_sol = (
            max(0, virtual_sol - calibration.quote_offset)
            if calibration and virtual_sol is not None
            else None
        )
        common = _common(self.descriptor.name, signature, received_at)
        await publish(
            TokenTrade(
                **common,
                event_id=deterministic_event_id(signature, 0, "pumpportal_trade"),
                source_sequence=0,
                mint=mint,
                signature=signature,
                side=(
                    TradeSide.BUY
                    if str(message.get("txType", "")).lower() == "buy"
                    else TradeSide.SELL
                ),
                token_amount=token_amount,
                quote_amount=sol_amount,
                quote_asset=WRAPPED_SOL_MINT,
                quote_mint=WRAPPED_SOL_MINT,
                wallet=_address(message.get("traderPublicKey")),
                market=curve,
                virtual_token_reserves=virtual_tokens,
                virtual_quote_reserves=virtual_sol,
                real_token_reserves=real_tokens,
                real_quote_reserves=real_sol,
            )
        )
        await self._publish_progress(mint, curve, signature, virtual_tokens, common, publish)
        if (
            mint not in self._pinned_position_mints
            and mint not in self._research_until
            and self._candidate_trade_counts[mint]
            >= self._settings.pumpportal_max_trade_events_per_candidate
        ):
            if (
                len(self._candidate_buyers.get(mint, set())) >= 4
                and self._candidate_flow.get(mint, Decimal(0)) > 0
                and self._candidate_trade_counts[mint]
                < self._settings.pumpportal_max_trade_events_per_candidate * 4
            ):
                self._subscriptions[mint] = max(self._subscriptions[mint], monotonic() + 15)
            else:
                await self._unsubscribe(connection, mint, reason="candidate_event_cap")

    async def _publish_progress(
        self,
        mint: str,
        curve: str | None,
        signature: str,
        virtual_tokens: int | None,
        common: dict[str, Any],
        publish: PublishEvent,
    ) -> None:
        calibration = self._calibrations.get(mint)
        initial = calibration.initial_real_tokens if calibration else None
        if initial is None or virtual_tokens is None or initial <= 0 or calibration is None:
            return
        remaining = min(initial, max(0, virtual_tokens - calibration.token_offset))
        progress = Decimal(initial - remaining) * 100 / Decimal(initial)
        bucket = int(progress)
        if bucket == self._last_progress_bucket.get(mint, -1):
            return
        self._last_progress_bucket[mint] = bucket
        await publish(
            TokenLifecycleChanged(
                **common,
                event_id=deterministic_event_id(signature, 1, "pumpportal_progress"),
                source_sequence=1,
                mint=mint,
                lifecycle=(
                    MarketLifecycle.FINAL_STRETCH
                    if progress >= self._settings.pump_final_stretch_percent
                    else MarketLifecycle.BONDING_CURVE
                ),
                validation_state=MarketValidationState.INSUFFICIENT_DATA,
                bonding_progress_percent=progress,
                market=curve,
                quote_mint=WRAPPED_SOL_MINT,
                reason="pumpportal_rpc_calibrated_real_reserve_progress",
            )
        )

    async def _handle_migration(self, message: dict[str, Any], publish: PublishEvent) -> None:
        mint = _address(message.get("mint"))
        signature = _signature(message.get("signature"))
        if mint is None or signature is None:
            return
        received_at = utc_now()
        common = _common(self.descriptor.name, signature, received_at)
        pool = _address(message.get("pool"))
        if pool:
            self._pools[mint] = pool
        self._calibrations.pop(mint, None)
        await publish(
            TokenLifecycleChanged(
                **common,
                event_id=deterministic_event_id(signature, 0, "pumpportal_migration"),
                source_sequence=0,
                mint=mint,
                lifecycle=MarketLifecycle.POST_GRADUATION,
                validation_state=MarketValidationState.INSUFFICIENT_DATA,
                bonding_progress_percent=Decimal(100),
                market=_address(message.get("pool")),
                quote_mint=WRAPPED_SOL_MINT,
                reason="third_party_migration_requires_rpc_pool_validation",
            )
        )

    async def _subscribe_candidate(self, connection: WebSocketConnection, mint: str) -> None:
        was_halted = self._budget_halted
        self._reset_daily_budget_if_needed()
        if was_halted and not self._budget_halted:
            await self._publish_health(ProviderConnectionState.CONNECTED)
        if self._budget_halted:
            return
        now = monotonic()
        if now < self._next_candidate_subscription_at:
            return
        if mint in self._subscriptions:
            if mint not in self._pinned_position_mints and mint not in self._research_until:
                self._subscriptions[mint] = (
                    monotonic() + self._settings.pumpportal_candidate_observation_seconds
                )
            return
        candidate_mints = [
            item
            for item in self._subscriptions
            if item not in self._pinned_position_mints and item not in self._research_until
        ]
        while len(candidate_mints) >= self._settings.pumpportal_max_active_token_subscriptions:
            oldest = min(candidate_mints, key=self._subscriptions.__getitem__)
            await self._unsubscribe(connection, oldest, reason="active_subscription_cap")
            candidate_mints.remove(oldest)
        self._subscriptions[mint] = now + self._settings.pumpportal_candidate_observation_seconds
        self._candidate_trade_counts[mint] = 0
        subscription_delay = self._candidate_subscription_delay_seconds()
        self._next_candidate_subscription_at = now + subscription_delay
        await self._send(connection, "subscribeTokenTrade", [mint])
        if (
            self._calibrate is not None
            and mint in self._creation_context
            and mint not in self._calibrations
        ):
            curve, signature = self._creation_context[mint]
            try:
                calibration = await self._calibrate(mint, curve, signature)
                if calibration is not None:
                    self._calibrations[mint] = calibration
            except Exception as error:
                self._logger.warning(
                    "curve_calibration_unavailable", mint=mint, error_code=type(error).__name__
                )
        self._logger.info(
            "pumpportal_candidate_subscribed",
            mint=mint,
            observation_seconds=(self._settings.pumpportal_candidate_observation_seconds),
            next_candidate_in_seconds=(subscription_delay),
            events_today=self._trade_events_today,
            daily_limit=self._settings.pumpportal_max_trade_events_per_day,
        )

    def _candidate_subscription_delay_seconds(self) -> float:
        """Pace paid candidate events across the rest of the UTC budget day."""
        configured = float(self._settings.pumpportal_candidate_subscription_interval_seconds)
        daily_limit = self._settings.pumpportal_max_trade_events_per_day
        if daily_limit <= 0:
            return configured
        reserve_fraction = self._settings.pumpportal_trade_budget_reserve_percent / Decimal(100)
        candidate_limit = max(
            1,
            int(Decimal(daily_limit) * (Decimal(1) - reserve_fraction)),
        )
        remaining_candidate_events = candidate_limit - self._trade_events_today
        now = utc_now()
        day_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=UTC)
        seconds_remaining = max(1.0, 86400.0 - (now - day_start).total_seconds())
        if remaining_candidate_events <= 0:
            return max(configured, seconds_remaining)
        projected = (
            seconds_remaining
            * self._settings.pumpportal_max_trade_events_per_candidate
            / remaining_candidate_events
        )
        return max(configured, min(projected, 15.0))

    def _candidate_event_limit(self) -> int | None:
        """Zero means metered continuous mode, bounded only by provider balance."""
        daily_limit = self._settings.pumpportal_max_trade_events_per_day
        if daily_limit == 0:
            return None
        return max(
            1,
            int(daily_limit * (1 - self._settings.pumpportal_trade_budget_reserve_percent / 100)),
        )

    async def _expire_subscriptions(self, connection: WebSocketConnection) -> None:
        now = monotonic()
        for mint, until in tuple(self._research_until.items()):
            if until <= now:
                self._research_until.pop(mint, None)
        for mint, expires_at in tuple(self._subscriptions.items()):
            if (
                expires_at <= now and mint not in self._pinned_position_mints
            ) or self._budget_halted:
                await self._unsubscribe(
                    connection,
                    mint,
                    reason="daily_budget" if self._budget_halted else "observation_timeout",
                )

    async def _unsubscribe(
        self, connection: WebSocketConnection, mint: str, *, reason: str
    ) -> None:
        observed_events = self._candidate_trade_counts.get(mint, 0)
        self._subscriptions.pop(mint, None)
        self._candidate_trade_counts.pop(mint, None)
        self._candidate_buyers.pop(mint, None)
        self._candidate_flow.pop(mint, None)
        await self._send(connection, "unsubscribeTokenTrade", [mint])
        self._logger.info(
            "pumpportal_candidate_observation_completed",
            mint=mint,
            reason=reason,
            observed_trade_events=observed_events,
            events_today=self._trade_events_today,
        )

    @staticmethod
    async def _send(
        connection: WebSocketConnection, method: str, keys: list[str] | None = None
    ) -> None:
        payload: dict[str, object] = {"method": method}
        if keys is not None:
            payload["keys"] = keys
        await connection.send(json.dumps(payload, separators=(",", ":")))

    def _reset_daily_budget_if_needed(self) -> None:
        today = utc_now().date()
        if today != self._trade_budget_day:
            self._trade_budget_day = today
            self._trade_events_today = 0
            self._budget_halted = False
            self._next_budget_notice_at = 0.0
            self._next_candidate_subscription_at = 0.0

    def _endpoint(self) -> str:
        key = quote(self._api_key, safe="")
        separator = "&" if "?" in str(self._settings.pumpportal_ws_url) else "?"
        return f"{self._settings.pumpportal_ws_url}{separator}api-key={key}"

    async def _publish_budget_halted(self) -> None:
        await self._publish_health(
            ProviderConnectionState.DEGRADED,
            error_code="pumpportal_daily_trade_budget_reached",
            confirmed_capabilities=frozenset(
                {
                    ProviderCapability.TOKEN_DISCOVERY,
                    ProviderCapability.MEME_LIFECYCLE,
                }
            ),
            unavailable_capabilities=frozenset({ProviderCapability.TOKEN_TRADES}),
        )

    async def _publish_health(
        self,
        state: ProviderConnectionState,
        *,
        error_code: str | None = None,
        http_status: int | None = None,
        confirmed_capabilities: frozenset[ProviderCapability] | None = None,
        unavailable_capabilities: frozenset[ProviderCapability] | None = None,
    ) -> None:
        if self._publish is None or self._last_health == (state, error_code, http_status):
            return
        self._last_health = (state, error_code, http_status)
        connected = state == ProviderConnectionState.CONNECTED
        capabilities = confirmed_capabilities if confirmed_capabilities is not None else frozenset()
        unavailable = (
            unavailable_capabilities
            if unavailable_capabilities is not None
            else frozenset()
            if connected
            else self.descriptor.requested_capabilities
        )
        await self._publish(
            ProviderHealthUpdated(
                provider=self.descriptor.name,
                source_event_at=utc_now(),
                state=state,
                confirmed_capabilities=frozenset(item.value for item in capabilities),
                unavailable_capabilities=frozenset(item.value for item in unavailable),
                reconnect_count=self._reconnect_count,
                error_code=error_code,
                http_status=http_status,
                rate_limited=http_status == 429,
            )
        )

    async def close(self) -> None:
        self._closed = True
        if self._connection is not None:
            await self._connection.close()
        await self._publish_health(ProviderConnectionState.DISCONNECTED)


def _parse_message(raw_message: str | bytes) -> dict[str, Any] | None:
    try:
        decoded = json.loads(raw_message)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return cast(dict[str, Any], decoded) if isinstance(decoded, dict) else None


def _portal_error_code(message: dict[str, Any]) -> str | None:
    errors = message.get("errors")
    detail = " ".join(str(item) for item in errors) if isinstance(errors, list) else ""
    status_message = str(message.get("message", ""))
    combined = f"{detail} {status_message}".lower()
    if not detail and not any(
        marker in combined for marker in ("error", "insufficient", "fund", "balance", "invalid api")
    ):
        return None
    if any(marker in combined for marker in ("fund", "balance", "insufficient")):
        return "pumpportal_trade_wallet_unfunded"
    if "api" in combined or "key" in combined or "auth" in combined:
        return "pumpportal_authentication_rejected"
    return "pumpportal_subscription_rejected"


def _common(provider: str, signature: str, received_at: datetime) -> dict[str, Any]:
    return {
        "provider": provider,
        "source_event_at": received_at.astimezone(UTC),
        "source_timestamp_estimated": True,
        "provider_received_at": received_at,
        "source_signature": signature,
    }


def _address(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text if is_solana_address(text) else None


def _signature(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text if 32 <= len(text) <= 128 else None


def _text(value: object, maximum: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:maximum] or None


def _raw_decimal(value: object, scale: Decimal) -> Decimal | None:
    try:
        raw = (Decimal(str(value)) * scale).to_integral_value(rounding=ROUND_DOWN)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return raw if raw > 0 else None


def _raw_amount(value: object, scale: Decimal) -> int | None:
    raw = _raw_decimal(value, scale)
    return int(raw) if raw is not None else None
