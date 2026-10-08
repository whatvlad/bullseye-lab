from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from memebot.core.clock import utc_now
from memebot.events.models import (
    DomainEvent,
    TokenLifecycleChanged,
    TokenTrade,
    TradeSide,
    parse_core_event,
)
from memebot.models.common import is_solana_address
from memebot.models.market import MarketLifecycle
from memebot.storage.database.models import (
    DomainEventRecord,
    TokenRecord,
    TokenTradeRecord,
    WalletRecord,
    WalletTokenOutcomeRecord,
    WalletTradeObservationRecord,
)

_ZERO = Decimal(0)
_HUNDRED = Decimal(100)


class WalletIntelligenceRepository:
    """Empirical wallet observations; never grants trading authority in Phase 8."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        early_entry_seconds: int = 30,
        candidate_min_launches: int = 3,
        scored_min_launches: int = 10,
        high_confidence_min_launches: int = 30,
        success_expansion_percent: Decimal = Decimal(50),
    ) -> None:
        self._sessions = sessions
        self._early_entry_seconds = early_entry_seconds
        self._candidate_min_launches = candidate_min_launches
        self._scored_min_launches = scored_min_launches
        self._high_confidence_min_launches = high_confidence_min_launches
        self._success_expansion_percent = success_expansion_percent

    async def handle(self, event: DomainEvent) -> dict[str, Any] | None:
        if isinstance(event, TokenTrade):
            return await self._record_trade(event)
        elif isinstance(event, TokenLifecycleChanged):
            await self._record_lifecycle(event)
        return None

    async def backfill_existing(
        self,
        *,
        limit: int = 2000,
        on_activity: Callable[[dict[str, Any]], None] | None = None,
    ) -> int:
        """Project already persisted wallet trades without external API calls."""
        # Limit the unprojected trade IDs before loading JSON payloads. Joining
        # payloads first made PostgreSQL probe hundreds of thousands of already
        # projected events for every one-row background batch.
        pending = (
            select(TokenTradeRecord.event_id, TokenTradeRecord.source_event_at)
            .outerjoin(
                WalletTradeObservationRecord,
                WalletTradeObservationRecord.event_id == TokenTradeRecord.event_id,
            )
            .where(
                TokenTradeRecord.wallet.is_not(None),
                WalletTradeObservationRecord.event_id.is_(None),
            )
            .order_by(TokenTradeRecord.source_event_at, TokenTradeRecord.event_id)
            .limit(limit)
            .subquery()
        )
        async with self._sessions() as session:
            records = (
                await session.scalars(
                    select(DomainEventRecord)
                    .join(pending, pending.c.event_id == DomainEventRecord.event_id)
                    .order_by(pending.c.source_event_at, pending.c.event_id)
                )
            ).all()
        processed = 0
        for record in records:
            event = parse_core_event(record.payload)
            if isinstance(event, TokenTrade):
                activity = await self.handle(event)
                if activity is not None and on_activity is not None:
                    on_activity(activity)
                processed += 1
        return processed

    async def reconcile_terminal_lifecycles(self, *, limit: int = 100) -> int:
        """Recover terminal flags from durable token state, including after restart."""
        async with self._sessions() as session, session.begin():
            rows = (
                await session.execute(
                    select(WalletTokenOutcomeRecord, TokenRecord)
                    .join(TokenRecord, TokenRecord.id == WalletTokenOutcomeRecord.token_id)
                    .where(
                        or_(
                            (TokenRecord.graduated_at.is_not(None))
                            & (WalletTokenOutcomeRecord.graduated.is_(False)),
                            (
                                TokenRecord.current_lifecycle
                                == MarketLifecycle.DEAD_OR_ILLIQUID.value
                            )
                            & (WalletTokenOutcomeRecord.liquidity_collapsed.is_(False)),
                        )
                    )
                    .limit(limit)
                )
            ).all()
            addresses = set()
            for outcome, token in rows:
                if token.graduated_at is not None:
                    outcome.graduated = True
                if token.current_lifecycle == MarketLifecycle.DEAD_OR_ILLIQUID.value:
                    outcome.liquidity_collapsed = True
                addresses.add(outcome.wallet_address)
            await session.flush()
            for address in addresses:
                wallet = await session.get(WalletRecord, address)
                if wallet is not None:
                    await self._refresh_metrics(session, wallet)
            return len(rows)

    async def set_seed(
        self, address: str, *, enabled: bool, label: str | None = None
    ) -> dict[str, Any]:
        if not is_solana_address(address):
            raise ValueError("invalid_solana_wallet")
        if label is not None and len(label.strip()) > 64:
            raise ValueError("wallet_label_too_long")
        now = utc_now()
        async with self._sessions() as session, session.begin():
            wallet = await session.get(WalletRecord, address)
            if wallet is None:
                wallet = WalletRecord(
                    address=address,
                    seeded=enabled,
                    label=label.strip() if label else None,
                    discovery_source="manual_seed",
                    status="observed",
                    first_seen_at=now,
                    last_seen_at=now,
                    observed_trade_count=0,
                    confidence="insufficient",
                )
                session.add(wallet)
            else:
                wallet.seeded = enabled
                if label is not None:
                    wallet.label = label.strip() or None
                if enabled:
                    wallet.discovery_source = "manual_seed"
            await session.flush()
            await self._refresh_metrics(session, wallet)
            return _wallet_payload(wallet)

    async def wallet_report(self, address: str) -> dict[str, Any] | None:
        async with self._sessions() as session, session.begin():
            wallet = await session.get(WalletRecord, address)
            if wallet is None:
                return None
            await self._refresh_metrics(session, wallet)
            outcome_rows = (
                await session.execute(
                    select(WalletTokenOutcomeRecord, TokenRecord)
                    .join(TokenRecord, TokenRecord.id == WalletTokenOutcomeRecord.token_id)
                    .where(WalletTokenOutcomeRecord.wallet_address == address)
                    .order_by(WalletTokenOutcomeRecord.first_buy_at.desc())
                )
            ).all()
            activity_rows = (
                await session.execute(
                    select(WalletTradeObservationRecord, TokenRecord)
                    .join(TokenRecord, TokenRecord.id == WalletTradeObservationRecord.token_id)
                    .where(WalletTradeObservationRecord.wallet_address == address)
                    .order_by(WalletTradeObservationRecord.occurred_at.desc())
                    .limit(30)
                )
            ).all()
            payload = _wallet_payload(wallet)
            payload["recent_token_outcomes"] = [
                _wallet_token_payload(outcome, token) for outcome, token in outcome_rows[:20]
            ]
            payload["recent_activity"] = [
                _wallet_trade_payload(trade, token) for trade, token in activity_rows
            ]
            payload["portfolio"] = _wallet_portfolio_payload(
                [outcome for outcome, _token in outcome_rows]
            )
            return payload

    async def ranked_wallets(
        self, *, limit: int = 20, seeded_only: bool = False
    ) -> list[dict[str, Any]]:
        async with self._sessions() as session, session.begin():
            query = select(WalletRecord)
            if seeded_only:
                query = query.where(WalletRecord.seeded.is_(True))
            wallet_result = await session.scalars(
                query.order_by(
                    WalletRecord.seeded.desc(),
                    WalletRecord.latest_alpha_score.desc().nullslast(),
                    WalletRecord.observed_trade_count.desc(),
                ).limit(limit)
            )
            wallets = list(wallet_result.all())
            for wallet in wallets:
                await self._refresh_metrics(session, wallet)
            wallets.sort(
                key=lambda item: (
                    item.seeded,
                    item.latest_alpha_score or Decimal(-1),
                    item.observed_trade_count,
                ),
                reverse=True,
            )
            return [_wallet_payload(item) for item in wallets]

    async def _record_trade(self, event: TokenTrade) -> dict[str, Any] | None:
        if event.wallet is None:
            return None
        async with self._sessions() as session, session.begin():
            existing = await session.get(WalletTradeObservationRecord, event.event_id)
            if existing is not None:
                return None
            token = await _required_token(session, event.mint)
            wallet = await session.get(WalletRecord, event.wallet)
            if wallet is None:
                wallet = WalletRecord(
                    address=event.wallet,
                    seeded=False,
                    discovery_source="pump_trade_stream",
                    status="observed",
                    first_seen_at=event.source_event_at,
                    last_seen_at=event.source_event_at,
                    observed_trade_count=0,
                    confidence="insufficient",
                )
                session.add(wallet)
            wallet.first_seen_at = min(_as_utc(wallet.first_seen_at), event.source_event_at)
            wallet.last_seen_at = max(_as_utc(wallet.last_seen_at), event.source_event_at)
            wallet.observed_trade_count += 1
            price = event.quote_amount / event.token_amount
            session.add(
                WalletTradeObservationRecord(
                    event_id=event.event_id,
                    wallet_address=event.wallet,
                    token_id=token.id,
                    mint=event.mint,
                    side=event.side.value,
                    token_amount_raw=event.token_amount,
                    quote_amount_raw=event.quote_amount,
                    price_raw=price,
                    source_slot=event.source_slot,
                    occurred_at=event.source_event_at,
                )
            )
            outcome = await session.scalar(
                select(WalletTokenOutcomeRecord).where(
                    WalletTokenOutcomeRecord.wallet_address == event.wallet,
                    WalletTokenOutcomeRecord.token_id == token.id,
                )
            )
            if event.side == TradeSide.BUY:
                outcome = self._apply_buy(outcome, wallet, token, event, price)
                if outcome.id is None:
                    session.add(outcome)
            elif outcome is not None:
                self._apply_sell(outcome, event)
            await session.flush()
            crossed_wallets = await self._update_token_excursions(
                session, token.id, price, event.source_event_at
            )
            await self._refresh_metrics(session, wallet)
            for address in crossed_wallets[:100]:
                crossed = await session.get(WalletRecord, address)
                if crossed is not None and crossed.address != wallet.address:
                    await self._refresh_metrics(session, crossed)
            if not wallet.seeded:
                return None
            return _tracked_wallet_activity(wallet, token, event, outcome)

    def _apply_buy(
        self,
        outcome: WalletTokenOutcomeRecord | None,
        wallet: WalletRecord,
        token: TokenRecord,
        event: TokenTrade,
        price: Decimal,
    ) -> WalletTokenOutcomeRecord:
        if outcome is None:
            created_at = token.source_created_at
            delay = (
                max(0, int((event.source_event_at - _as_utc(created_at)).total_seconds()))
                if created_at is not None
                else None
            )
            return WalletTokenOutcomeRecord(
                wallet_address=wallet.address,
                token_id=token.id,
                mint=token.mint,
                first_buy_at=event.source_event_at,
                first_buy_price_raw=price,
                last_price_raw=price,
                entry_delay_seconds=delay,
                early_entry=(delay <= self._early_entry_seconds if delay is not None else None),
                buy_count=1,
                sell_count=0,
                total_token_bought_raw=event.token_amount,
                total_quote_spent_raw=event.quote_amount,
                total_token_sold_raw=_ZERO,
                total_quote_received_raw=_ZERO,
                remaining_token_raw=event.token_amount,
                remaining_cost_quote_raw=event.quote_amount,
                realized_pnl_quote_raw=_ZERO,
                highest_price_raw=price,
                lowest_price_raw=price,
                mfe_percent=_ZERO,
                mae_percent=_ZERO,
                last_activity_at=event.source_event_at,
                graduated=token.graduated_at is not None,
                liquidity_collapsed=(
                    token.current_lifecycle == MarketLifecycle.DEAD_OR_ILLIQUID.value
                ),
            )
        outcome.buy_count += 1
        outcome.total_token_bought_raw += event.token_amount
        outcome.total_quote_spent_raw += event.quote_amount
        outcome.remaining_token_raw += event.token_amount
        outcome.remaining_cost_quote_raw += event.quote_amount
        outcome.last_activity_at = event.source_event_at
        outcome.last_price_raw = price
        outcome.closed_at = None
        outcome.holding_seconds = None
        return outcome

    @staticmethod
    def _apply_sell(outcome: WalletTokenOutcomeRecord, event: TokenTrade) -> None:
        if outcome.remaining_token_raw <= 0:
            return
        sold = min(event.token_amount, outcome.remaining_token_raw)
        fraction = sold / event.token_amount
        proceeds = event.quote_amount * fraction
        allocated_cost = outcome.remaining_cost_quote_raw * sold / outcome.remaining_token_raw
        outcome.sell_count += 1
        outcome.total_token_sold_raw += sold
        outcome.total_quote_received_raw += proceeds
        outcome.remaining_token_raw -= sold
        outcome.remaining_cost_quote_raw -= allocated_cost
        outcome.realized_pnl_quote_raw += proceeds - allocated_cost
        outcome.last_activity_at = event.source_event_at
        if outcome.remaining_token_raw <= 0:
            outcome.remaining_token_raw = _ZERO
            outcome.remaining_cost_quote_raw = _ZERO
            outcome.closed_at = event.source_event_at
            outcome.holding_seconds = max(
                0,
                int((event.source_event_at - _as_utc(outcome.first_buy_at)).total_seconds()),
            )
            outcome.realized_return_percent = (
                outcome.realized_pnl_quote_raw / outcome.total_quote_spent_raw * _HUNDRED
                if outcome.total_quote_spent_raw > 0
                else None
            )

    async def _update_token_excursions(
        self,
        session: AsyncSession,
        token_id: Any,
        price: Decimal,
        observed_at: datetime,
    ) -> list[str]:
        outcome_result = await session.scalars(
            select(WalletTokenOutcomeRecord).where(
                WalletTokenOutcomeRecord.token_id == token_id,
                WalletTokenOutcomeRecord.first_buy_at <= observed_at,
            )
        )
        outcomes = list(outcome_result.all())
        crossed: list[str] = []
        threshold_multiplier = Decimal(1) + self._success_expansion_percent / _HUNDRED
        for outcome in outcomes:
            outcome.last_price_raw = price
            outcome.highest_price_raw = max(outcome.highest_price_raw, price)
            outcome.lowest_price_raw = min(outcome.lowest_price_raw, price)
            outcome.mfe_percent = _return_percent(
                outcome.highest_price_raw, outcome.first_buy_price_raw
            )
            outcome.mae_percent = _return_percent(
                outcome.lowest_price_raw, outcome.first_buy_price_raw
            )
            if (
                outcome.first_expansion_50_at is None
                and price >= outcome.first_buy_price_raw * threshold_multiplier
            ):
                outcome.first_expansion_50_at = observed_at
                outcome.lead_seconds_before_50_percent = max(
                    0,
                    int((observed_at - _as_utc(outcome.first_buy_at)).total_seconds()),
                )
                crossed.append(outcome.wallet_address)
        return crossed

    async def _record_lifecycle(self, event: TokenLifecycleChanged) -> None:
        # Curve progress updates do not change any wallet outcome fields.
        # Recalculating up to 100 wallets for each percentage tick blocks live
        # market ingestion while reproducing already stored trade projections.
        if event.lifecycle not in {
            MarketLifecycle.GRADUATION,
            MarketLifecycle.POST_GRADUATION,
            MarketLifecycle.DEAD_OR_ILLIQUID,
        }:
            return
        async with self._sessions() as session, session.begin():
            token = await _required_token(session, event.mint)
            outcomes = (
                await session.scalars(
                    select(WalletTokenOutcomeRecord).where(
                        WalletTokenOutcomeRecord.token_id == token.id
                    )
                )
            ).all()
            addresses: set[str] = set()
            for outcome in outcomes:
                if event.lifecycle in {
                    MarketLifecycle.GRADUATION,
                    MarketLifecycle.POST_GRADUATION,
                }:
                    outcome.graduated = True
                if event.lifecycle == MarketLifecycle.DEAD_OR_ILLIQUID:
                    outcome.liquidity_collapsed = True
                addresses.add(outcome.wallet_address)
            for address in list(addresses)[:100]:
                wallet = await session.get(WalletRecord, address)
                if wallet is not None:
                    await self._refresh_metrics(session, wallet)

    async def _refresh_metrics(self, session: AsyncSession, wallet: WalletRecord) -> dict[str, Any]:
        outcome_result = await session.scalars(
            select(WalletTokenOutcomeRecord).where(
                WalletTokenOutcomeRecord.wallet_address == wallet.address
            )
        )
        outcomes = list(outcome_result.all())
        metrics = _calculate_metrics(
            outcomes,
            observed_trades=wallet.observed_trade_count,
            candidate_min_launches=self._candidate_min_launches,
            scored_min_launches=self._scored_min_launches,
            high_confidence_min_launches=self._high_confidence_min_launches,
            success_expansion_percent=self._success_expansion_percent,
        )
        wallet.latest_alpha_score = Decimal(metrics["alpha_score"])
        wallet.confidence = str(metrics["confidence"])
        wallet.status = str(metrics["status"])
        wallet.metrics_json = metrics
        wallet.metrics_calculated_at = utc_now()
        return metrics


def _calculate_metrics(
    outcomes: list[WalletTokenOutcomeRecord],
    *,
    observed_trades: int,
    candidate_min_launches: int,
    scored_min_launches: int,
    high_confidence_min_launches: int,
    success_expansion_percent: Decimal,
) -> dict[str, Any]:
    sample = len(outcomes)
    closed = [item for item in outcomes if item.closed_at is not None]
    returns = [
        item.realized_return_percent for item in closed if item.realized_return_percent is not None
    ]
    early = [item for item in outcomes if item.early_entry is True]
    early_successes = [item for item in early if item.mfe_percent >= success_expansion_percent]
    rugs = [item for item in outcomes if item.liquidity_collapsed]
    positive = [item for item in returns if item > 0]
    above_25 = [item for item in returns if item >= 25]
    above_50 = [item for item in returns if item >= 50]
    holding = [Decimal(item.holding_seconds) for item in closed if item.holding_seconds is not None]
    entry_delays = [
        Decimal(item.entry_delay_seconds)
        for item in outcomes
        if item.entry_delay_seconds is not None
    ]
    drawdowns = [item.mae_percent for item in outcomes]
    early_frequency = _rate(len(early), sample)
    early_success_rate = _rate(len(early_successes), sample)
    rug_rate = _rate(len(rugs), sample)
    median_return = _median(returns)
    average_return = _mean(returns)
    consistency = _consistency(returns)
    components = {
        "early_entry_frequency": early_frequency,
        "early_success_frequency": early_success_rate,
        "realized_performance": _clamp(Decimal(50) + (median_return or _ZERO)),
        "adverse_selection_safety": _HUNDRED - rug_rate,
        "consistency": consistency,
    }
    raw_alpha = (
        components["early_entry_frequency"] * Decimal("0.30")
        + components["early_success_frequency"] * Decimal("0.25")
        + components["realized_performance"] * Decimal("0.20")
        + components["adverse_selection_safety"] * Decimal("0.15")
        + components["consistency"] * Decimal("0.10")
    )
    reliability = min(Decimal(1), Decimal(sample) / Decimal(20))
    alpha = Decimal(50) + (raw_alpha - Decimal(50)) * reliability
    confidence = (
        "high"
        if sample >= high_confidence_min_launches
        else "medium"
        if sample >= scored_min_launches
        else "low"
        if sample >= candidate_min_launches
        else "insufficient"
    )
    status = (
        "scored"
        if sample >= scored_min_launches
        else "candidate"
        if sample >= candidate_min_launches and len(early_successes) >= 2
        else "observed"
    )
    return {
        "version": 1,
        "status": status,
        "confidence": confidence,
        "sample_size": sample,
        "observed_trades": observed_trades,
        "closed_samples": len(closed),
        "win_rate_positive_percent": str(_rate(len(positive), len(returns))),
        "win_rate_25_percent": str(_rate(len(above_25), len(returns))),
        "win_rate_50_percent": str(_rate(len(above_50), len(returns))),
        "median_return_percent": str(median_return) if median_return is not None else None,
        "average_return_percent": str(average_return) if average_return is not None else None,
        "median_holding_seconds": str(_median(holding)) if holding else None,
        "average_entry_delay_seconds": str(_mean(entry_delays)) if entry_delays else None,
        "early_entry_frequency_percent": str(early_frequency),
        "early_success_frequency_percent": str(early_success_rate),
        "rug_exposure_percent": str(rug_rate),
        "median_drawdown_percent": str(_median(drawdowns)) if drawdowns else None,
        "profitable_launches": len(positive),
        "graduated_launches": sum(item.graduated for item in outcomes),
        "alpha_score": str(alpha.quantize(Decimal("0.01"))),
        "raw_alpha_score": str(raw_alpha.quantize(Decimal("0.01"))),
        "reliability_factor": str(reliability.quantize(Decimal("0.0001"))),
        "components": {
            key: str(value.quantize(Decimal("0.01"))) for key, value in components.items()
        },
        "trading_influence_enabled": False,
    }


def _wallet_payload(wallet: WalletRecord) -> dict[str, Any]:
    return {
        "address": wallet.address,
        "label": wallet.label,
        "seeded": wallet.seeded,
        "tracked": wallet.seeded,
        "discovery_source": wallet.discovery_source,
        "status": wallet.status,
        "confidence": wallet.confidence,
        "observed_trade_count": wallet.observed_trade_count,
        "alpha_score": (
            str(wallet.latest_alpha_score) if wallet.latest_alpha_score is not None else None
        ),
        "first_seen_at": _as_utc(wallet.first_seen_at).isoformat(),
        "last_seen_at": _as_utc(wallet.last_seen_at).isoformat(),
        "metrics": wallet.metrics_json,
        "trading_influence_enabled": False,
    }


def _wallet_token_payload(
    item: WalletTokenOutcomeRecord, token: TokenRecord | None = None
) -> dict[str, Any]:
    unrealized = _unrealized_pnl(item)
    return {
        "mint": item.mint,
        "name": token.name if token is not None else None,
        "symbol": token.symbol if token is not None else None,
        "first_buy_at": _as_utc(item.first_buy_at).isoformat(),
        "entry_delay_seconds": item.entry_delay_seconds,
        "early_entry": item.early_entry,
        "buy_count": item.buy_count,
        "sell_count": item.sell_count,
        "realized_return_percent": (
            str(item.realized_return_percent) if item.realized_return_percent is not None else None
        ),
        "realized_pnl_sol": str(item.realized_pnl_quote_raw / Decimal(1_000_000_000)),
        "unrealized_pnl_sol": str(unrealized / Decimal(1_000_000_000)),
        "remaining_token_raw": str(item.remaining_token_raw),
        "last_price_raw": str(item.last_price_raw) if item.last_price_raw is not None else None,
        "mfe_percent": str(item.mfe_percent),
        "mae_percent": str(item.mae_percent),
        "lead_seconds_before_50_percent": item.lead_seconds_before_50_percent,
        "holding_seconds": item.holding_seconds,
        "graduated": item.graduated,
        "liquidity_collapsed": item.liquidity_collapsed,
        "closed": item.closed_at is not None,
    }


def _wallet_trade_payload(
    trade: WalletTradeObservationRecord, token: TokenRecord
) -> dict[str, Any]:
    return {
        "event_id": str(trade.event_id),
        "mint": trade.mint,
        "name": token.name,
        "symbol": token.symbol,
        "side": trade.side,
        "token_amount_raw": str(trade.token_amount_raw),
        "quote_amount_sol": str(trade.quote_amount_raw / Decimal(1_000_000_000)),
        "price_raw": str(trade.price_raw),
        "source_slot": trade.source_slot,
        "occurred_at": _as_utc(trade.occurred_at).isoformat(),
    }


def _wallet_portfolio_payload(outcomes: list[WalletTokenOutcomeRecord]) -> dict[str, Any]:
    open_outcomes = [item for item in outcomes if item.remaining_token_raw > 0]
    realized = sum((item.realized_pnl_quote_raw for item in outcomes), start=_ZERO)
    unrealized = sum((_unrealized_pnl(item) for item in open_outcomes), start=_ZERO)
    return {
        "open_token_count": len(open_outcomes),
        "realized_pnl_sol": str(realized / Decimal(1_000_000_000)),
        "unrealized_pnl_sol": str(unrealized / Decimal(1_000_000_000)),
        "total_pnl_sol": str((realized + unrealized) / Decimal(1_000_000_000)),
    }


def _unrealized_pnl(item: WalletTokenOutcomeRecord) -> Decimal:
    if item.last_price_raw is None or item.remaining_token_raw <= 0:
        return _ZERO
    return item.remaining_token_raw * item.last_price_raw - item.remaining_cost_quote_raw


def _tracked_wallet_activity(
    wallet: WalletRecord,
    token: TokenRecord,
    event: TokenTrade,
    outcome: WalletTokenOutcomeRecord | None,
) -> dict[str, Any]:
    return {
        "wallet": wallet.address,
        "label": wallet.label,
        "mint": token.mint,
        "name": token.name,
        "symbol": token.symbol,
        "side": event.side.value,
        "token_amount_raw": str(event.token_amount),
        "quote_amount_sol": str(event.quote_amount / Decimal(1_000_000_000)),
        "signature": event.signature,
        "occurred_at": event.source_event_at.isoformat(),
        "realized_pnl_sol": (
            str(outcome.realized_pnl_quote_raw / Decimal(1_000_000_000))
            if outcome is not None
            else None
        ),
        "unrealized_pnl_sol": (
            str(_unrealized_pnl(outcome) / Decimal(1_000_000_000)) if outcome is not None else None
        ),
        "remaining_token_raw": (str(outcome.remaining_token_raw) if outcome is not None else None),
    }


async def _required_token(session: AsyncSession, mint: str) -> TokenRecord:
    token = await session.scalar(
        select(TokenRecord).where(TokenRecord.network == "solana", TokenRecord.mint == mint)
    )
    if token is None:
        raise RuntimeError("wallet_token_not_found")
    return token


def _return_percent(price: Decimal, baseline: Decimal) -> Decimal:
    return (price / baseline - Decimal(1)) * _HUNDRED


def _rate(count: int, total: int) -> Decimal:
    return Decimal(count) / Decimal(total) * _HUNDRED if total else _ZERO


def _mean(values: list[Decimal]) -> Decimal | None:
    return sum(values, start=_ZERO) / Decimal(len(values)) if values else None


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    return (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / Decimal(2)
    )


def _consistency(returns: list[Decimal]) -> Decimal:
    if len(returns) < 2:
        return Decimal(50)
    average = _mean(returns)
    assert average is not None
    variance = sum(((item - average) ** 2 for item in returns), start=_ZERO) / Decimal(len(returns))
    return _clamp(_HUNDRED - variance.sqrt())


def _clamp(value: Decimal) -> Decimal:
    return min(_HUNDRED, max(_ZERO, value))


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
