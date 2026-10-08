from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Any
from uuid import UUID, uuid5

from memebot.events.models import (
    MarketFeatureSnapshotCreated,
    TokenLifecycleChanged,
    TokenTrade,
    TradeSide,
)
from memebot.intelligence.features.models import RollingWindowMetrics
from memebot.market_state import MarketStateTracker
from memebot.models.market import MarketLifecycle, MarketValidationState

_FEATURE_EVENT_NAMESPACE = UUID("bdd640de-3adf-57bf-9625-b4070c1cc901")
_ZERO = Decimal(0)
_ONE_HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class _TradePoint:
    event_id: UUID
    observed_at: datetime
    source_slot: int | None
    side: TradeSide
    token_amount: Decimal
    quote_amount: Decimal
    wallet: str | None
    real_quote_reserves: int | None
    marginal_price: Decimal | None = None
    price_evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def price_raw(self) -> Decimal | None:
        return self.marginal_price

    @property
    def order_key(self) -> tuple[datetime, int, str]:
        return self.observed_at, self.source_slot or 0, str(self.event_id)


@dataclass(slots=True)
class _TokenState:
    trades: deque[_TradePoint] = field(default_factory=deque)
    seen_event_ids: set[UUID] = field(default_factory=set)
    watermark: datetime | None = None
    last_snapshot_bucket: int | None = None
    lifecycle: MarketLifecycle = MarketLifecycle.UNKNOWN
    validation_state: MarketValidationState = MarketValidationState.DISCOVERED
    lifecycle_changed_at: datetime | None = None
    last_lifecycle_slot: int | None = None
    bonding_progress_percent: Decimal | None = None
    market: str | None = None


class RollingFeatureEngine:
    """Bounded event-time rolling features with deterministic snapshot output."""

    def __init__(
        self,
        windows_seconds: tuple[int, ...],
        *,
        snapshot_interval_seconds: int = 1,
        max_lateness_seconds: int = 5,
        max_token_states: int = 10000,
        state_tracker: MarketStateTracker | None = None,
    ) -> None:
        if not windows_seconds or tuple(sorted(set(windows_seconds))) != windows_seconds:
            raise ValueError("windows_seconds must be sorted, unique, and non-empty")
        if windows_seconds[0] <= 0:
            raise ValueError("rolling windows must be positive")
        if snapshot_interval_seconds <= 0 or max_lateness_seconds < 0:
            raise ValueError("invalid snapshot interval or lateness")
        if max_token_states <= 0:
            raise ValueError("max_token_states must be positive")
        self._windows = windows_seconds
        self._maximum_window = windows_seconds[-1]
        self._snapshot_interval = snapshot_interval_seconds
        self._max_lateness = max_lateness_seconds
        self._states: dict[str, _TokenState] = {}
        self._max_token_states = max_token_states
        self._pinned_mints: set[str] = set()
        self._state_tracker = state_tracker
        self.evicted_token_states = 0

    def pin_mint(self, mint: str) -> None:
        self._pinned_mints.add(mint)

    def unpin_mint(self, mint: str) -> None:
        self._pinned_mints.discard(mint)

    def has_open_position(self, mint: str) -> bool:
        """Position pins are maintained by startup restoration and order events."""
        return mint in self._pinned_mints

    def invalidate_price_history(self, mint: str | None = None) -> None:
        """A receive gap must not be bridged by an apparently complete window."""
        states = self._states.values() if mint is None else [self._states.get(mint)]
        for state in states:
            if state is None:
                continue
            state.trades = deque(
                replace(
                    point,
                    marginal_price=None,
                    price_evidence={
                        **point.price_evidence,
                        "data_quality": "feed_gap",
                    },
                )
                for point in state.trades
            )
            state.last_snapshot_bucket = None

    def _state(self, mint: str) -> _TokenState:
        # LRU across mints; rolling time eviction alone never freed inactive mints.
        existing = self._states.pop(mint, None)
        if existing is not None:
            self._states[mint] = existing
            return existing
        if len(self._states) >= self._max_token_states:
            victim = next((key for key in self._states if key not in self._pinned_mints), None)
            if victim is None:
                raise RuntimeError("feature_state_capacity_exhausted_by_pinned_positions")
            del self._states[victim]
            self.evicted_token_states += 1
        state = _TokenState()
        self._states[mint] = state
        return state

    def ingest_trade(self, event: TokenTrade) -> MarketFeatureSnapshotCreated | None:
        if event.normalized_state.continuity_status == "SLOT_REGRESSION":
            return None
        state = self._state(event.mint)
        if event.event_id in state.seen_event_ids:
            return None
        if state.watermark is not None and event.source_event_at < state.watermark - timedelta(
            seconds=self._max_lateness
        ):
            return None

        point = _TradePoint(
            event_id=event.event_id,
            observed_at=event.source_event_at,
            source_slot=event.source_slot,
            side=event.side,
            token_amount=event.token_amount,
            quote_amount=event.quote_amount,
            wallet=event.wallet,
            real_quote_reserves=event.normalized_state.quote_reserve,
            marginal_price=event.normalized_state.observational_price,
            price_evidence={
                **event.normalized_state.evidence(),
                "price_source": (
                    "normalized_observational_reserves"
                    if event.normalized_state.observational_price is not None
                    else "unavailable_normalized_state"
                ),
                "provider": event.provider,
                "source_timestamp": event.source_event_at,
                "received_timestamp": event.provider_received_at or event.ingested_at,
                "price_source_disagreement_pct": None,
                "data_quality": "source_time_estimated"
                if event.source_timestamp_estimated or "pumpportal" in event.provider
                else "source_time_reported",
            },
        )
        self._insert_ordered(state, point)
        state.seen_event_ids.add(event.event_id)
        state.watermark = max(state.watermark or event.source_event_at, event.source_event_at)
        self._evict_expired(state)

        bucket = int(state.watermark.timestamp()) // self._snapshot_interval
        if state.last_snapshot_bucket is not None and bucket <= state.last_snapshot_bucket:
            return None
        state.last_snapshot_bucket = bucket
        return self._build_snapshot(event.mint, state, event)

    def current_snapshot(self, event: TokenTrade) -> MarketFeatureSnapshotCreated | None:
        """Evaluate every fresh trade for exits without persisting every snapshot."""
        state = self._states.get(event.mint)
        if state is None or state.watermark != event.source_event_at:
            return None
        return self._build_snapshot(event.mint, state, event)

    def seed_lifecycle(
        self,
        mint: str,
        *,
        lifecycle: MarketLifecycle,
        validation_state: MarketValidationState,
        changed_at: datetime | None,
        source_slot: int | None,
        bonding_progress_percent: Decimal | None,
        market: str | None,
    ) -> None:
        """Restore durable lifecycle context without manufacturing a snapshot."""
        state = self._state(mint)
        state.lifecycle = lifecycle
        state.validation_state = validation_state
        state.lifecycle_changed_at = changed_at
        state.last_lifecycle_slot = source_slot
        state.bonding_progress_percent = bonding_progress_percent
        state.market = market
        state.watermark = changed_at

    def ingest_lifecycle(
        self,
        event: TokenLifecycleChanged,
    ) -> MarketFeatureSnapshotCreated | None:
        state = self._state(event.mint)
        is_current = (
            event.source_slot is None
            or state.last_lifecycle_slot is None
            or event.source_slot >= state.last_lifecycle_slot
        )
        if not is_current:
            return None
        changed = (
            state.lifecycle != event.lifecycle
            or state.validation_state != event.validation_state
            or state.bonding_progress_percent != event.bonding_progress_percent
            or state.market != event.market
        )
        state.lifecycle = event.lifecycle
        state.validation_state = event.validation_state
        state.lifecycle_changed_at = event.source_event_at
        state.last_lifecycle_slot = event.source_slot or state.last_lifecycle_slot
        state.bonding_progress_percent = event.bonding_progress_percent
        state.market = event.market
        state.watermark = max(state.watermark or event.source_event_at, event.source_event_at)
        self._evict_expired(state)
        if not changed:
            return None
        state.last_snapshot_bucket = int(state.watermark.timestamp()) // self._snapshot_interval
        return self._build_snapshot(event.mint, state, event)

    @staticmethod
    def _insert_ordered(state: _TokenState, point: _TradePoint) -> None:
        if not state.trades or state.trades[-1].order_key <= point.order_key:
            state.trades.append(point)
            return
        for index, existing in enumerate(state.trades):
            if point.order_key < existing.order_key:
                state.trades.insert(index, point)
                return
        state.trades.append(point)

    def _evict_expired(self, state: _TokenState) -> None:
        assert state.watermark is not None
        cutoff = state.watermark - timedelta(seconds=self._maximum_window)
        while state.trades and state.trades[0].observed_at < cutoff:
            expired = state.trades.popleft()
            state.seen_event_ids.discard(expired.event_id)

    def _build_snapshot(
        self,
        mint: str,
        state: _TokenState,
        trigger: TokenTrade | TokenLifecycleChanged,
    ) -> MarketFeatureSnapshotCreated:
        assert state.watermark is not None
        windows = tuple(self._window_metrics(state, window) for window in self._windows)
        latest_price = state.trades[-1].price_raw if state.trades else None
        current = (
            self._state_tracker.states.get(state.market or "") if self._state_tracker else None
        )
        if current is not None and current.observational_price is None:
            latest_price = None
            windows = tuple(
                metric.model_copy(
                    update={
                        "price_change_percent": None,
                        "price_velocity_percent_per_second": None,
                        "price_acceleration_percent_per_second2": None,
                        "latest_price_return_percent": None,
                        "close_price_raw": None,
                    }
                )
                for metric in windows
            )
        lifecycle_age = None
        if state.lifecycle_changed_at is not None:
            lifecycle_age = max(
                0,
                int((state.watermark - state.lifecycle_changed_at).total_seconds()),
            )
        return MarketFeatureSnapshotCreated(
            price_evidence={
                **state.trades[-1].price_evidence,
                # A newer RPC snapshot cannot relabel the older tick's price.
                **(
                    current.evidence()
                    if current is not None and current.observational_price is None
                    else {}
                ),
                "price_age_ms": int(
                    (trigger.ingested_at - state.trades[-1].observed_at).total_seconds() * 1000
                ),
                "feed_age_ms": int(
                    (trigger.ingested_at - state.trades[-1].observed_at).total_seconds() * 1000
                ),
            }
            if state.trades
            else {"data_quality": "no_trades", "price_age_ms": None, "feed_age_ms": None},
            event_id=uuid5(_FEATURE_EVENT_NAMESPACE, str(trigger.event_id)),
            provider="rolling_feature_engine",
            source_event_at=state.watermark,
            source_timestamp_estimated=trigger.source_timestamp_estimated,
            provider_received_at=trigger.provider_received_at,
            ingested_at=trigger.ingested_at,
            correlation_id=trigger.correlation_id,
            source_sequence=trigger.source_sequence,
            source_signature=trigger.source_signature,
            source_slot=trigger.source_slot,
            mint=mint,
            trigger_event_id=trigger.event_id,
            lifecycle=state.lifecycle,
            validation_state=state.validation_state,
            lifecycle_age_seconds=lifecycle_age,
            bonding_progress_percent=state.bonding_progress_percent,
            market=state.market,
            latest_price_raw=latest_price,
            windows=windows,
        )

    def _window_metrics(self, state: _TokenState, window_seconds: int) -> RollingWindowMetrics:
        assert state.watermark is not None
        cutoff = state.watermark - timedelta(seconds=window_seconds)
        trades = [trade for trade in state.trades if trade.observed_at >= cutoff]
        buys = [trade for trade in trades if trade.side == TradeSide.BUY]
        sells = [trade for trade in trades if trade.side == TradeSide.SELL]
        buy_volume = sum((trade.quote_amount for trade in buys), start=_ZERO)
        sell_volume = sum((trade.quote_amount for trade in sells), start=_ZERO)
        total_volume = buy_volume + sell_volume
        amounts = [trade.quote_amount for trade in trades]
        unique_buyers = {trade.wallet for trade in buys if trade.wallet is not None}
        unique_sellers = {trade.wallet for trade in sells if trade.wallet is not None}
        open_price = trades[0].price_raw if trades else None
        close_price = trades[-1].price_raw if trades else None
        price_change = _percent_change(open_price, close_price)
        price_velocity = _price_velocity(trades)
        price_points = [trade for trade in trades if trade.price_raw is not None]
        missing_prices = len(trades) - len(price_points)
        if missing_prices:
            price_change = price_velocity = None

        half_seconds = Decimal(window_seconds) / 2
        midpoint = state.watermark - timedelta(seconds=window_seconds / 2)
        previous = [trade for trade in trades if trade.observed_at < midpoint]
        recent = [trade for trade in trades if trade.observed_at >= midpoint]
        previous_volume = sum((trade.quote_amount for trade in previous), start=_ZERO)
        recent_volume = sum((trade.quote_amount for trade in recent), start=_ZERO)
        volume_acceleration = (
            (recent_volume / half_seconds) - (previous_volume / half_seconds)
        ) / half_seconds
        transaction_acceleration = (
            (Decimal(len(recent)) / half_seconds) - (Decimal(len(previous)) / half_seconds)
        ) / half_seconds
        previous_buyers = {
            trade.wallet
            for trade in previous
            if trade.side == TradeSide.BUY and trade.wallet is not None
        }
        recent_buyers = {
            trade.wallet
            for trade in recent
            if trade.side == TradeSide.BUY and trade.wallet is not None
        }
        buyer_acceleration = (
            (Decimal(len(recent_buyers)) / half_seconds)
            - (Decimal(len(previous_buyers)) / half_seconds)
        ) / half_seconds
        pressure_acceleration = (_buy_pressure(recent) - _buy_pressure(previous)) / half_seconds
        previous_price_velocity = _price_velocity(previous)
        recent_price_velocity = _price_velocity(recent)
        reserve_points = [trade for trade in trades if trade.real_quote_reserves is not None]
        reserve_change: Decimal | None = None
        reserve_velocity: Decimal | None = None
        if len(reserve_points) >= 2:
            reserve_change = Decimal(
                _required(reserve_points[-1].real_quote_reserves)
                - _required(reserve_points[0].real_quote_reserves)
            )
            elapsed = Decimal(
                str(
                    (reserve_points[-1].observed_at - reserve_points[0].observed_at).total_seconds()
                )
            )
            if elapsed > 0:
                reserve_velocity = reserve_change / elapsed
        buyer_volumes: dict[str, Decimal] = {}
        for trade in buys:
            if trade.wallet is not None:
                buyer_volumes[trade.wallet] = (
                    buyer_volumes.get(trade.wallet, _ZERO) + trade.quote_amount
                )
        attributed_buy_volume = sum(buyer_volumes.values(), start=_ZERO)
        buyer_attribution = (
            attributed_buy_volume * _ONE_HUNDRED / buy_volume if buy_volume > 0 else _ZERO
        )
        largest_buyer_share = (
            max(buyer_volumes.values()) / attributed_buy_volume
            if attributed_buy_volume > 0
            else None
        )
        buyer_hhi = (
            sum((volume / attributed_buy_volume) ** 2 for volume in buyer_volumes.values())
            if attributed_buy_volume > 0
            else None
        )

        return RollingWindowMetrics(
            window_seconds=window_seconds,
            trade_count=len(trades),
            buy_count=len(buys),
            sell_count=len(sells),
            unique_buyers=len(unique_buyers),
            unique_sellers=len(unique_sellers),
            buy_volume_quote_raw=buy_volume,
            sell_volume_quote_raw=sell_volume,
            total_volume_quote_raw=total_volume,
            average_trade_quote_raw=(total_volume / len(trades) if trades else None),
            median_trade_quote_raw=(median(amounts) if amounts else None),
            largest_buy_quote_raw=max((trade.quote_amount for trade in buys), default=None),
            largest_sell_quote_raw=max((trade.quote_amount for trade in sells), default=None),
            buy_sell_count_ratio=(Decimal(len(buys)) / Decimal(len(sells)) if sells else None),
            buy_sell_volume_ratio=(buy_volume / sell_volume if sell_volume else None),
            flow_imbalance=((buy_volume - sell_volume) / total_volume if total_volume else None),
            open_price_raw=open_price,
            close_price_raw=close_price,
            price_change_percent=price_change,
            price_sample_count=len(price_points),
            missing_price_sample_count=missing_prices,
            price_observation_span_seconds=(
                Decimal(
                    str(
                        (price_points[-1].observed_at - price_points[0].observed_at).total_seconds()
                    )
                )
                if len(price_points) >= 2
                else _ZERO
            ),
            price_velocity_percent_per_second=price_velocity,
            price_acceleration_percent_per_second2=(recent_price_velocity - previous_price_velocity)
            / half_seconds
            if recent_price_velocity is not None and previous_price_velocity is not None
            else None,
            volume_velocity_quote_raw_per_second=(total_volume / Decimal(window_seconds)),
            volume_acceleration_quote_raw_per_second2=volume_acceleration,
            transaction_rate_per_second=Decimal(len(trades)) / Decimal(window_seconds),
            transaction_rate_acceleration_per_second2=transaction_acceleration,
            unique_buyer_rate_acceleration_per_second2=buyer_acceleration,
            buy_pressure_acceleration_per_second=pressure_acceleration,
            quote_reserve_change_raw=reserve_change,
            quote_reserve_velocity_raw_per_second=reserve_velocity,
            largest_buyer_volume_share=largest_buyer_share,
            buyer_volume_hhi=buyer_hhi,
            buyer_wallet_attribution_percent=buyer_attribution,
            latest_price_return_percent=_latest_return_percent(trades),
            latest_sell_size_mad_score=_latest_sell_mad_score(trades),
            observation_span_seconds=(
                Decimal(str((trades[-1].observed_at - trades[0].observed_at).total_seconds()))
                if len(trades) >= 2
                else _ZERO
            ),
            latest_sell_quote_raw=(
                trades[-1].quote_amount if trades and trades[-1].side == TradeSide.SELL else None
            ),
            latest_sell_liquidity_fraction=(
                trades[-1].quote_amount / Decimal(trades[-1].real_quote_reserves)
                if trades and trades[-1].side == TradeSide.SELL and trades[-1].real_quote_reserves
                else None
            ),
        )


def _percent_change(first: Decimal | None, last: Decimal | None) -> Decimal | None:
    if first is None or last is None or first == 0:
        return None
    return ((last - first) / first) * _ONE_HUNDRED


def _price_velocity(trades: list[_TradePoint]) -> Decimal | None:
    if len(trades) < 2:
        return None
    elapsed = Decimal(str((trades[-1].observed_at - trades[0].observed_at).total_seconds()))
    if elapsed <= 0:
        return None
    change = _percent_change(trades[0].price_raw, trades[-1].price_raw)
    return change / elapsed if change is not None else None


def _buy_pressure(trades: list[_TradePoint]) -> Decimal:
    buy_volume = sum(
        (trade.quote_amount for trade in trades if trade.side == TradeSide.BUY),
        start=_ZERO,
    )
    sell_volume = sum(
        (trade.quote_amount for trade in trades if trade.side == TradeSide.SELL),
        start=_ZERO,
    )
    total = buy_volume + sell_volume
    return (buy_volume - sell_volume) / total if total else _ZERO


def _latest_return_percent(trades: list[_TradePoint]) -> Decimal | None:
    if len(trades) < 2:
        return None
    return _percent_change(trades[-2].price_raw, trades[-1].price_raw)


def _latest_sell_mad_score(trades: list[_TradePoint]) -> Decimal | None:
    if not trades or trades[-1].side != TradeSide.SELL:
        return None
    sell_sizes = [trade.quote_amount for trade in trades[:-1] if trade.side == TradeSide.SELL]
    if len(sell_sizes) < 3:
        return None
    center = median(sell_sizes)
    deviation = median([abs(value - center) for value in sell_sizes])
    latest = trades[-1].quote_amount
    # Near-identical prints cannot turn a rounding difference into an extreme sell.
    scale = max(Decimal("1.4826") * deviation, center * Decimal("0.10"), Decimal(1))
    return max(_ZERO, (latest - center) / scale)


def _required(value: int | None) -> int:
    if value is None:
        raise ValueError("required reserve value is missing")
    return value
