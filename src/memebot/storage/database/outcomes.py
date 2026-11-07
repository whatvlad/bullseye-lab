from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from memebot.events.models import (
    DomainEvent,
    PaperOrderCompleted,
    StrategyDecisionCreated,
    TokenLifecycleChanged,
    TokenTrade,
)
from memebot.market_price import trade_mark
from memebot.models.market import MarketLifecycle
from memebot.models.paper import PaperOrderSide, PaperOrderStatus, PositionEffect
from memebot.models.strategy import StrategyDecisionAction
from memebot.storage.database.models import (
    DecisionOutcomeRecord,
    MarketFeatureSnapshotRecord,
    PaperOrderRecord,
    PaperPositionRecord,
    TokenRecord,
    TokenRiskAssessmentRecord,
    TradeOutcomeRecord,
)

FUTURE_RETURN_HORIZONS_SECONDS = (5, 10, 30, 60, 120, 300, 600, 1800, 3600)
_HORIZON_TOLERANCE_SECONDS = 60
_MAX_TRACKING_SECONDS = max(FUTURE_RETURN_HORIZONS_SECONDS) + _HORIZON_TOLERANCE_SECONDS


class OutcomeRecorder:
    """Record post-decision counterfactuals and taken paper-trade outcomes."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def handle(self, event: DomainEvent) -> None:
        if not isinstance(
            event,
            (StrategyDecisionCreated, TokenTrade, TokenLifecycleChanged, PaperOrderCompleted),
        ):
            return
        async with self._sessions() as session, session.begin():
            await self.handle_in_session(session, event)

    async def handle_in_session(self, session: AsyncSession, event: DomainEvent) -> None:
        """Project outcomes in the event transaction; no second commit per tick."""
        if isinstance(event, StrategyDecisionCreated):
            await self._record_decision(session, event)
        elif isinstance(event, TokenTrade):
            await self._observe_trade(session, event)
        elif isinstance(event, TokenLifecycleChanged):
            await self._observe_lifecycle(session, event)
        elif isinstance(event, PaperOrderCompleted):
            await self._record_paper_order(session, event)

    async def summary(self) -> dict[str, Any]:
        await self.reconcile_positions()
        async with self._sessions() as session:
            decisions = (await session.scalars(select(DecisionOutcomeRecord))).all()
            trades = (await session.scalars(select(TradeOutcomeRecord))).all()
        closed = [item for item in trades if item.status == "closed"]
        winners = [
            item for item in closed if item.realized_pnl is not None and item.realized_pnl > 0
        ]
        losers = [
            item for item in closed if item.realized_pnl is not None and item.realized_pnl < 0
        ]
        skipped = [item for item in decisions if item.execution_status in {"skipped", "watch"}]
        skipped_winners = [
            item for item in skipped if item.mfe_percent is not None and item.mfe_percent > 0
        ]
        return {
            "decision_count": len(decisions),
            "skipped_or_watch_count": len(skipped),
            "skipped_with_positive_excursion": len(skipped_winners),
            "taken_trade_count": len(trades),
            "open_trade_count": len(trades) - len(closed),
            "closed_trade_count": len(closed),
            "winning_trade_count": len(winners),
            "losing_trade_count": len(losers),
            "realized_pnl": str(
                sum(
                    (item.realized_pnl for item in closed if item.realized_pnl is not None),
                    start=Decimal(0),
                )
            ),
        }

    async def latest_decisions(self, *, limit: int = 20) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            records = (
                await session.scalars(
                    select(DecisionOutcomeRecord)
                    .order_by(DecisionOutcomeRecord.decided_at.desc())
                    .limit(limit)
                )
            ).all()
        return [_decision_payload(item) for item in records]

    async def latest_trades(self, *, limit: int = 20) -> list[dict[str, Any]]:
        await self.reconcile_positions()
        async with self._sessions() as session:
            records = (
                await session.scalars(
                    select(TradeOutcomeRecord)
                    .order_by(TradeOutcomeRecord.entry_at.desc())
                    .limit(limit)
                )
            ).all()
        return [_trade_payload(item) for item in records]

    async def daily_report(self, *, as_of: datetime | None = None) -> dict[str, Any]:
        await self.reconcile_positions()
        current = (as_of or datetime.now(UTC)).astimezone(UTC)
        day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        async with self._sessions() as session:
            trades = list(
                (
                    await session.scalars(
                        select(TradeOutcomeRecord).where(
                            TradeOutcomeRecord.entry_at >= day_start,
                            TradeOutcomeRecord.entry_at <= current,
                        )
                    )
                ).all()
            )
            orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord).where(
                            PaperOrderRecord.created_at >= day_start,
                            PaperOrderRecord.created_at <= current,
                        )
                    )
                ).all()
            )
        closed = [item for item in trades if item.status == "closed"]
        winners = [item for item in closed if (item.realized_pnl or Decimal(0)) > 0]
        pnl = sum((item.realized_pnl or Decimal(0) for item in closed), start=Decimal(0))
        exits: dict[str, int] = {}
        for item in closed:
            reason = item.exit_reason or "unknown"
            exits[reason] = exits.get(reason, 0) + 1
        rejected: dict[str, int] = {}
        for order in orders:
            if order.status != "rejected":
                continue
            reason = order.rejection_reason or "unknown"
            rejected[reason] = rejected.get(reason, 0) + 1
        return {
            "date": day_start.date().isoformat(),
            "trades_opened": len(trades),
            "trades_closed": len(closed),
            "trades_still_open": len(trades) - len(closed),
            "wins": len(winners),
            "losses": len(closed) - len(winners),
            "win_rate_percent": (
                str(Decimal(len(winners)) * 100 / Decimal(len(closed))) if closed else None
            ),
            "realized_pnl": str(pnl),
            "average_mfe_percent": (
                str(sum((item.mfe_percent for item in trades), start=Decimal(0)) / len(trades))
                if trades
                else None
            ),
            "average_mae_percent": (
                str(sum((item.mae_percent for item in trades), start=Decimal(0)) / len(trades))
                if trades
                else None
            ),
            "exit_reasons": exits,
            "top_rejections": dict(
                sorted(rejected.items(), key=lambda item: item[1], reverse=True)[:5]
            ),
        }

    async def _record_decision(self, session: AsyncSession, event: StrategyDecisionCreated) -> None:
        if await session.get(DecisionOutcomeRecord, event.event_id) is not None:
            return
        token = await _required_token(session, event.mint)
        feature = (
            await session.get(MarketFeatureSnapshotRecord, event.feature_event_id)
            if event.feature_event_id is not None
            else None
        )
        risk = await session.get(TokenRiskAssessmentRecord, event.risk_event_id)
        execution_status = _initial_execution_status(event)
        session.add(
            DecisionOutcomeRecord(
                decision_event_id=event.event_id,
                token_id=token.id,
                mint=event.mint,
                strategy_key=event.strategy_key,
                action=event.action.value,
                active_strategy=event.active_strategy,
                decided_at=event.source_event_at,
                baseline_price_raw=feature.latest_price_raw if feature is not None else None,
                baseline_market=feature.market_address
                if feature is not None
                else token.current_market,
                baseline_lifecycle=(
                    feature.lifecycle if feature is not None else token.current_lifecycle
                ),
                feature_snapshot_json=_feature_snapshot(feature),
                risk_snapshot_json=_risk_snapshot(risk),
                score_snapshot_json=event.score.model_dump(mode="json"),
                decision_reasons=list(event.reasons),
                execution_status=execution_status,
                horizon_returns_json={},
                graduated=token.graduated_at is not None,
                graduated_at=token.graduated_at,
                liquidity_collapsed=(
                    token.current_lifecycle == MarketLifecycle.DEAD_OR_ILLIQUID.value
                ),
            )
        )

    async def _observe_trade(self, session: AsyncSession, event: TokenTrade) -> None:
        price = trade_mark(event)
        if (
            event.normalized_state.state_source == "native_event"
            and event.normalized_state.observational_price is None
        ):
            return
        token = await _required_token(session, event.mint)
        lower_bound = event.source_event_at - timedelta(seconds=_MAX_TRACKING_SECONDS)
        decisions = (
            await session.scalars(
                select(DecisionOutcomeRecord).where(
                    DecisionOutcomeRecord.token_id == token.id,
                    DecisionOutcomeRecord.baseline_price_raw.is_not(None),
                    DecisionOutcomeRecord.decided_at <= event.source_event_at,
                    DecisionOutcomeRecord.decided_at >= lower_bound,
                )
            )
        ).all()
        for decision_outcome in decisions:
            _update_decision_market_outcome(decision_outcome, price, event.source_event_at)
        trades = (
            await session.scalars(
                select(TradeOutcomeRecord).where(
                    TradeOutcomeRecord.token_id == token.id,
                    or_(
                        TradeOutcomeRecord.status == "open",
                        TradeOutcomeRecord.exit_at >= lower_bound,
                    ),
                    TradeOutcomeRecord.entry_at <= event.source_event_at,
                )
            )
        ).all()
        for trade_outcome in trades:
            if trade_outcome.status == "closed":
                if (
                    trade_outcome.exit_at is not None
                    and _as_utc(trade_outcome.exit_at) < event.source_event_at
                ):
                    update_post_exit(trade_outcome, price, event.source_event_at)
                continue
            trade_outcome.highest_price_raw = max(trade_outcome.highest_price_raw, price)
            trade_outcome.lowest_price_raw = min(trade_outcome.lowest_price_raw, price)
            trade_outcome.mfe_percent = _return_percent(
                trade_outcome.highest_price_raw, trade_outcome.actual_entry_price_raw
            )
            trade_outcome.mae_percent = _return_percent(
                trade_outcome.lowest_price_raw, trade_outcome.actual_entry_price_raw
            )

    async def _observe_lifecycle(self, session: AsyncSession, event: TokenLifecycleChanged) -> None:
        token = await _required_token(session, event.mint)
        decisions = (
            await session.scalars(
                select(DecisionOutcomeRecord).where(
                    DecisionOutcomeRecord.token_id == token.id,
                    DecisionOutcomeRecord.decided_at <= event.source_event_at,
                )
            )
        ).all()
        trades = (
            await session.scalars(
                select(TradeOutcomeRecord).where(TradeOutcomeRecord.token_id == token.id)
            )
        ).all()
        if event.lifecycle in {MarketLifecycle.GRADUATION, MarketLifecycle.POST_GRADUATION}:
            for decision_outcome in decisions:
                decision_outcome.graduated = True
                decision_outcome.graduated_at = (
                    decision_outcome.graduated_at or event.source_event_at
                )
            for trade_outcome in trades:
                trade_outcome.graduated = True
        if event.lifecycle == MarketLifecycle.DEAD_OR_ILLIQUID:
            for decision_outcome in decisions:
                decision_outcome.liquidity_collapsed = True
                decision_outcome.liquidity_collapsed_at = (
                    decision_outcome.liquidity_collapsed_at or event.source_event_at
                )
            for trade_outcome in trades:
                trade_outcome.liquidity_collapsed = True

    async def _record_paper_order(self, session: AsyncSession, event: PaperOrderCompleted) -> None:
        result = event.result
        if event.decision_event_id is not None:
            decision = await session.get(DecisionOutcomeRecord, event.decision_event_id)
            if decision is not None:
                decision.order_event_id = event.event_id
                decision.execution_status = (
                    "filled" if result.status == PaperOrderStatus.FILLED else "rejected"
                )
                decision.execution_rejection_reason = result.rejection_reason
        if result.status != PaperOrderStatus.FILLED or result.fill is None:
            return
        if result.side == PaperOrderSide.BUY:
            await self._record_trade_entry(session, event)
        elif result.position_effect == PositionEffect.CLOSE:
            await self._record_trade_exit(session, event)

    async def _record_trade_entry(self, session: AsyncSession, event: PaperOrderCompleted) -> None:
        fill = event.result.fill
        assert fill is not None
        position = await session.scalar(
            select(PaperPositionRecord).where(
                PaperPositionRecord.portfolio_id == event.portfolio_id,
                PaperPositionRecord.mint == event.mint,
                PaperPositionRecord.status == "open",
            )
        )
        if position is None or await session.get(TradeOutcomeRecord, position.id) is not None:
            return
        decision = (
            await session.get(DecisionOutcomeRecord, event.decision_event_id)
            if event.decision_event_id is not None
            else None
        )
        session.add(
            TradeOutcomeRecord(
                position_id=position.id,
                portfolio_id=position.portfolio_id,
                token_id=position.token_id,
                mint=position.mint,
                strategy_key=position.strategy_key,
                entry_decision_event_id=event.decision_event_id,
                entry_order_event_id=event.event_id,
                entry_reasons=(
                    decision.decision_reasons if decision is not None else ["manual_paper_buy"]
                ),
                feature_snapshot_json=(
                    decision.feature_snapshot_json if decision is not None else None
                ),
                risk_snapshot_json=(decision.risk_snapshot_json if decision is not None else None),
                score_snapshot_json=(
                    decision.score_snapshot_json if decision is not None else None
                ),
                entry_at=fill.filled_at,
                expected_entry_price_raw=fill.expected_fill_price_raw,
                actual_entry_price_raw=fill.actual_fill_price_raw,
                entry_cost_portfolio=position.remaining_cost_basis,
                entry_fees_portfolio=fill.total_fee_portfolio,
                entry_slippage_bps=fill.latency_slippage_bps,
                entry_latency_ms=fill.simulated_latency_ms,
                highest_price_raw=fill.actual_fill_price_raw,
                lowest_price_raw=fill.actual_fill_price_raw,
                mfe_percent=Decimal(0),
                mae_percent=Decimal(0),
                status="open",
                graduated=False,
                liquidity_collapsed=False,
            )
        )

    async def _record_trade_exit(self, session: AsyncSession, event: PaperOrderCompleted) -> None:
        fill = event.result.fill
        assert fill is not None
        row = (
            await session.execute(
                select(PaperPositionRecord, TradeOutcomeRecord)
                .join(
                    TradeOutcomeRecord,
                    TradeOutcomeRecord.position_id == PaperPositionRecord.id,
                )
                .where(
                    PaperPositionRecord.portfolio_id == event.portfolio_id,
                    PaperPositionRecord.mint == event.mint,
                    PaperPositionRecord.status == "closed",
                    TradeOutcomeRecord.status == "open",
                )
                .order_by(PaperPositionRecord.closed_at.desc())
                .limit(1)
            )
        ).first()
        if row is None:
            return
        position, outcome = row
        outcome.status = "closed"
        outcome.exit_order_event_id = event.event_id
        outcome.exit_at = fill.filled_at
        outcome.exit_reason = event.result.exit_reason
        outcome.expected_exit_price_raw = fill.expected_fill_price_raw
        outcome.actual_exit_price_raw = fill.actual_fill_price_raw
        outcome.realized_pnl = position.realized_pnl
        outcome.pnl_percent = (
            position.realized_pnl / outcome.entry_cost_portfolio * Decimal(100)
            if outcome.entry_cost_portfolio > 0
            else None
        )
        outcome.holding_seconds = max(
            0,
            int((_as_utc(fill.filled_at) - _as_utc(outcome.entry_at)).total_seconds()),
        )

    async def reconcile_positions(self) -> int:
        """Repair historical outcome rows whose projected position is already closed."""
        repaired = 0
        async with self._sessions() as session, session.begin():
            rows = (
                await session.execute(
                    select(PaperPositionRecord, TradeOutcomeRecord)
                    .join(
                        TradeOutcomeRecord,
                        TradeOutcomeRecord.position_id == PaperPositionRecord.id,
                    )
                    .where(
                        PaperPositionRecord.status == "closed",
                        TradeOutcomeRecord.status == "open",
                    )
                )
            ).all()
            for position, outcome in rows:
                order = await session.scalar(
                    select(PaperOrderRecord)
                    .where(
                        PaperOrderRecord.portfolio_id == position.portfolio_id,
                        PaperOrderRecord.mint == position.mint,
                        PaperOrderRecord.side == "sell",
                        PaperOrderRecord.status == "filled",
                        PaperOrderRecord.position_effect == "close",
                        PaperOrderRecord.filled_at == position.closed_at,
                    )
                    .limit(1)
                )
                outcome.status = "closed"
                outcome.exit_at = position.closed_at
                outcome.realized_pnl = position.realized_pnl
                outcome.pnl_percent = (
                    position.realized_pnl / outcome.entry_cost_portfolio * Decimal(100)
                    if outcome.entry_cost_portfolio > 0
                    else None
                )
                if position.closed_at is not None:
                    outcome.holding_seconds = max(
                        0,
                        int(
                            (
                                _as_utc(position.closed_at) - _as_utc(outcome.entry_at)
                            ).total_seconds()
                        ),
                    )
                if order is not None:
                    outcome.exit_order_event_id = order.event_id
                    outcome.exit_reason = order.exit_reason
                    fill = order.fill_json or {}
                    expected = fill.get("expected_fill_price_raw")
                    actual = fill.get("actual_fill_price_raw")
                    outcome.expected_exit_price_raw = (
                        Decimal(str(expected)) if expected is not None else None
                    )
                    outcome.actual_exit_price_raw = (
                        Decimal(str(actual)) if actual is not None else None
                    )
                repaired += 1
        return repaired


def _initial_execution_status(event: StrategyDecisionCreated) -> str:
    if event.action == StrategyDecisionAction.SKIP:
        return "skipped"
    if event.action == StrategyDecisionAction.WATCH:
        return "watch"
    return "pending" if event.active_strategy else "shadow_candidate"


def _update_decision_market_outcome(
    outcome: DecisionOutcomeRecord, price: Decimal, observed_at: datetime
) -> None:
    baseline = outcome.baseline_price_raw
    if baseline is None or baseline <= 0:
        return
    if outcome.last_observed_at is not None and _as_utc(observed_at) < _as_utc(
        outcome.last_observed_at
    ):
        return
    outcome.last_observed_at = observed_at
    outcome.last_price_raw = price
    if outcome.maximum_price_raw is None or price > outcome.maximum_price_raw:
        outcome.maximum_price_raw = price
        outcome.post_decision_ath_at = observed_at
    if outcome.minimum_price_raw is None or price < outcome.minimum_price_raw:
        outcome.minimum_price_raw = price
    outcome.mfe_percent = _return_percent(outcome.maximum_price_raw, baseline)
    outcome.mae_percent = _return_percent(outcome.minimum_price_raw, baseline)
    elapsed = max(0, int((_as_utc(observed_at) - _as_utc(outcome.decided_at)).total_seconds()))
    horizons = dict(outcome.horizon_returns_json or {})
    for horizon in FUTURE_RETURN_HORIZONS_SECONDS:
        key = str(horizon)
        if elapsed >= horizon and key not in horizons:
            horizons[key] = {
                "return_percent": str(_return_percent(price, baseline))
                if elapsed - horizon <= min(_HORIZON_TOLERANCE_SECONDS, max(1, horizon / 10))
                else None,
                "price_raw": str(price),
                "observed_at": observed_at.isoformat(),
                "observed_delay_seconds": elapsed - horizon,
                "coverage": "observed"
                if elapsed - horizon <= min(_HORIZON_TOLERANCE_SECONDS, max(1, horizon / 10))
                else "gap",
            }
    outcome.horizon_returns_json = horizons


def _return_percent(price: Decimal, baseline: Decimal) -> Decimal:
    return ((price / baseline) - Decimal(1)) * Decimal(100)


def update_post_exit(outcome: TradeOutcomeRecord, price: Decimal, observed_at: datetime) -> None:
    if outcome.exit_at is None or outcome.actual_exit_price_raw is None:
        return
    observed_at = _as_utc(observed_at)
    if observed_at <= _as_utc(outcome.exit_at) or outcome.actual_exit_price_raw <= 0:
        return
    state = dict(outcome.post_exit_json or {})
    previous = state.get("last_observed_at")
    if previous and observed_at <= _as_utc(datetime.fromisoformat(previous)):
        return
    state["observations"] = int(state.get("observations", 0)) + 1
    state["last_observed_at"] = observed_at.isoformat()
    state["maximum_price_raw"] = str(
        max(Decimal(state.get("maximum_price_raw", str(price))), price)
    )
    state["minimum_price_raw"] = str(
        min(Decimal(state.get("minimum_price_raw", str(price))), price)
    )
    state["maximum_return_from_entry_percent"] = str(
        _return_percent(Decimal(state["maximum_price_raw"]), outcome.actual_entry_price_raw)
    )
    elapsed = (observed_at - _as_utc(outcome.exit_at)).total_seconds()
    horizons = dict(state.get("horizons", {}))
    for horizon in FUTURE_RETURN_HORIZONS_SECONDS:
        if elapsed >= horizon and str(horizon) not in horizons:
            valid = elapsed - horizon <= min(_HORIZON_TOLERANCE_SECONDS, max(1, horizon / 10))
            horizons[str(horizon)] = {
                "coverage": "observed" if valid else "gap",
                "return_percent": str(_return_percent(price, outcome.actual_exit_price_raw))
                if valid
                else None,
                "observed_delay_seconds": elapsed - horizon,
            }
    state["horizons"] = horizons
    outcome.post_exit_json = state


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def _required_token(session: AsyncSession, mint: str) -> TokenRecord:
    cache = session.info.get("token_cache")  # set by TokenRegistry.handle_many
    if cache is not None and mint in cache:
        return cast(TokenRecord, cache[mint])
    token = await session.scalar(
        select(TokenRecord).where(TokenRecord.network == "solana", TokenRecord.mint == mint)
    )
    if token is None:
        raise RuntimeError("outcome_token_not_found")
    if cache is not None:
        cache[mint] = token
    return token


def _feature_snapshot(record: MarketFeatureSnapshotRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "event_id": str(record.event_id),
        "observed_at": record.observed_at.isoformat(),
        "lifecycle": record.lifecycle,
        "validation_state": record.validation_state,
        "lifecycle_age_seconds": record.lifecycle_age_seconds,
        "bonding_progress_percent": (
            str(record.bonding_progress_percent)
            if record.bonding_progress_percent is not None
            else None
        ),
        "market": record.market_address,
        "latest_price_raw": (
            str(record.latest_price_raw) if record.latest_price_raw is not None else None
        ),
        "windows": record.windows_json,
    }


def _risk_snapshot(record: TokenRiskAssessmentRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "event_id": str(record.event_id),
        "assessed_at": record.assessed_at.isoformat(),
        "allowed": record.allowed,
        "risk_score": str(record.risk_score) if record.risk_score is not None else None,
        "data_completeness_percent": str(record.data_completeness_percent),
        "hard_reject_reasons": record.hard_reject_reasons,
        "warnings": record.warnings,
        "critical_unknowns": record.critical_unknowns,
        "evidence": record.evidence_json,
    }


def _decision_payload(record: DecisionOutcomeRecord) -> dict[str, Any]:
    return {
        "decision_event_id": str(record.decision_event_id),
        "mint": record.mint,
        "strategy": record.strategy_key,
        "action": record.action,
        "execution_status": record.execution_status,
        "decided_at": record.decided_at.isoformat(),
        "mfe_percent": str(record.mfe_percent) if record.mfe_percent is not None else None,
        "mae_percent": str(record.mae_percent) if record.mae_percent is not None else None,
        "horizon_returns": record.horizon_returns_json,
        "graduated": record.graduated,
        "liquidity_collapsed": record.liquidity_collapsed,
    }


def _trade_payload(record: TradeOutcomeRecord) -> dict[str, Any]:
    return {
        "position_id": str(record.position_id),
        "mint": record.mint,
        "strategy": record.strategy_key,
        "status": record.status,
        "entry_at": record.entry_at.isoformat(),
        "exit_at": record.exit_at.isoformat() if record.exit_at is not None else None,
        "exit_reason": record.exit_reason,
        "realized_pnl": str(record.realized_pnl) if record.realized_pnl is not None else None,
        "pnl_percent": str(record.pnl_percent) if record.pnl_percent is not None else None,
        "mfe_percent": str(record.mfe_percent),
        "mae_percent": str(record.mae_percent),
        "holding_seconds": record.holding_seconds,
        "post_exit": record.post_exit_json,
        "graduated": record.graduated,
        "liquidity_collapsed": record.liquidity_collapsed,
    }
