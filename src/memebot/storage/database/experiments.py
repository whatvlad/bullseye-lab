from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from memebot import __version__
from memebot.core.clock import utc_now
from memebot.paper.validation_gate import require_price_validation

from .models import (
    DecisionOutcomeRecord,
    ExperimentRunRecord,
    PaperOrderRecord,
    PaperPortfolioRecord,
    PaperPositionRecord,
    StrategyConfigurationRecord,
    StrategyDecisionRecord,
    TokenRiskAssessmentRecord,
    TradeOutcomeRecord,
    TradingControlRecord,
)


class ExperimentRepository:
    """Own clean, non-overlapping paper experiments and their reports."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def active(self) -> dict[str, Any] | None:
        async with self._sessions() as session:
            record = await session.scalar(
                select(ExperimentRunRecord)
                .where(ExperimentRunRecord.status == "active")
                .order_by(ExperimentRunRecord.started_at.desc())
                .limit(1)
            )
            return _experiment_payload(record) if record is not None else None

    async def list(self, *, limit: int = 20) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            records = (
                await session.scalars(
                    select(ExperimentRunRecord)
                    .order_by(ExperimentRunRecord.started_at.desc())
                    .limit(limit)
                )
            ).all()
        return [_experiment_payload(item) for item in records]

    async def start(
        self,
        *,
        name: str,
        initial_cash: Decimal,
        currency: str,
        settings_snapshot: dict[str, object],
        notes: str | None = None,
    ) -> dict[str, Any]:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("experiment name cannot be empty")
        require_price_validation(normalized_name, settings_snapshot)
        started_at = utc_now()
        async with self._sessions() as session, session.begin():
            if (
                await session.scalar(
                    select(ExperimentRunRecord.id).where(ExperimentRunRecord.status == "active")
                )
                is not None
            ):
                raise ValueError("an experiment is already active")
            if (
                await session.scalar(
                    select(ExperimentRunRecord.id).where(
                        ExperimentRunRecord.name == normalized_name
                    )
                )
                is not None
            ):
                raise ValueError("experiment name already exists")
            control = await session.get(TradingControlRecord, 1)
            if control is None:
                raise ValueError("trading control is not initialized; run bullseye discover once")
            if not control.entries_paused:
                raise ValueError("pause entries before starting an experiment")
            active_portfolio = await session.scalar(
                select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
            )
            if active_portfolio is not None:
                open_positions = await session.scalar(
                    select(func.count())
                    .select_from(PaperPositionRecord)
                    .where(
                        PaperPositionRecord.portfolio_id == active_portfolio.id,
                        PaperPositionRecord.status == "open",
                    )
                )
                if open_positions:
                    raise ValueError("close all positions before starting a clean experiment")
            strategy = await session.scalar(
                select(StrategyConfigurationRecord)
                .where(StrategyConfigurationRecord.strategy_key == control.active_strategy_key)
                .order_by(StrategyConfigurationRecord.version.desc())
                .limit(1)
            )
            if strategy is None:
                raise ValueError("active strategy configuration is unavailable")
            for portfolio in (
                await session.scalars(
                    select(PaperPortfolioRecord).where(PaperPortfolioRecord.active.is_(True))
                )
            ).all():
                portfolio.active = False
            portfolio = PaperPortfolioRecord(
                name=f"Experiment: {normalized_name}",
                currency=currency,
                initial_cash=initial_cash,
                cash_balance=initial_cash,
                realized_pnl=Decimal(0),
                active=True,
            )
            session.add(portfolio)
            await session.flush()
            strategy_snapshot = dict(strategy.configuration_json)
            strategy_snapshot["declared_active_for_execution"] = strategy_snapshot.get(
                "active_for_execution"
            )
            strategy_snapshot["active_for_execution"] = True
            strategy_snapshot["activation_source"] = "trading_control"
            snapshot = {
                "captured_at": started_at.isoformat(),
                "settings": settings_snapshot,
                "trading_control": {
                    "active_strategy_key": control.active_strategy_key,
                    "base_position_percent": str(control.base_position_percent),
                    "max_position_percent": str(control.max_position_percent),
                    "max_open_positions": control.max_open_positions,
                    "stop_loss_percent": str(control.stop_loss_percent),
                    "take_profit_percent": str(control.take_profit_percent),
                    "trailing_stop_percent": str(control.trailing_stop_percent),
                    "max_holding_seconds": control.max_holding_seconds,
                },
                "strategy": strategy_snapshot,
            }
            experiment = ExperimentRunRecord(
                name=normalized_name,
                status="active",
                portfolio_id=portfolio.id,
                strategy_key=control.active_strategy_key,
                strategy_version_id=strategy.version_id,
                application_version=__version__,
                configuration_snapshot_json=snapshot,
                started_at=started_at,
                notes=notes,
            )
            session.add(experiment)
            await session.flush()
            return _experiment_payload(experiment)

    async def stop(self) -> dict[str, Any]:
        async with self._sessions() as session, session.begin():
            experiment = await session.scalar(
                select(ExperimentRunRecord)
                .where(ExperimentRunRecord.status == "active")
                .order_by(ExperimentRunRecord.started_at.desc())
                .limit(1)
            )
            if experiment is None:
                raise ValueError("no active experiment")
            control = await session.get(TradingControlRecord, 1)
            if control is not None:
                control.entries_paused = True
                control.updated_by_telegram_user_id = 0
            open_positions = await session.scalar(
                select(func.count())
                .select_from(PaperPositionRecord)
                .where(
                    PaperPositionRecord.portfolio_id == experiment.portfolio_id,
                    PaperPositionRecord.status == "open",
                )
            )
            if open_positions:
                raise ValueError("experiment has open positions; close them before stopping")
            experiment.status = "stopped"
            experiment.stopped_at = utc_now()
            await session.flush()
            return _experiment_payload(experiment)

    async def report(self, name: str | None = None) -> dict[str, Any]:
        async with self._sessions() as session:
            query = select(ExperimentRunRecord)
            if name is None:
                query = query.order_by(ExperimentRunRecord.started_at.desc()).limit(1)
            else:
                query = query.where(ExperimentRunRecord.name == name)
            experiment = await session.scalar(query)
            if experiment is None:
                raise ValueError("experiment not found")
            report_end = experiment.stopped_at or utc_now()
            decisions = list(
                (
                    await session.scalars(
                        select(DecisionOutcomeRecord).where(
                            DecisionOutcomeRecord.decided_at >= experiment.started_at,
                            DecisionOutcomeRecord.decided_at <= report_end,
                        )
                    )
                ).all()
            )
            strategy_decisions = list(
                (
                    await session.scalars(
                        select(StrategyDecisionRecord).where(
                            StrategyDecisionRecord.decided_at >= experiment.started_at,
                            StrategyDecisionRecord.decided_at <= report_end,
                            StrategyDecisionRecord.active_strategy.is_(True),
                        )
                    )
                ).all()
            )
            trades = list(
                (
                    await session.scalars(
                        select(TradeOutcomeRecord)
                        .where(TradeOutcomeRecord.portfolio_id == experiment.portfolio_id)
                        .order_by(TradeOutcomeRecord.entry_at)
                    )
                ).all()
            )
            orders = list(
                (
                    await session.scalars(
                        select(PaperOrderRecord)
                        .where(PaperOrderRecord.portfolio_id == experiment.portfolio_id)
                        .order_by(PaperOrderRecord.created_at)
                    )
                ).all()
            )
            risk_assessments = list(
                (
                    await session.scalars(
                        select(TokenRiskAssessmentRecord).where(
                            TokenRiskAssessmentRecord.assessed_at >= experiment.started_at,
                            TokenRiskAssessmentRecord.assessed_at <= report_end,
                        )
                    )
                ).all()
            )
            portfolio = await session.get(PaperPortfolioRecord, experiment.portfolio_id)
            active_portfolio_id = await session.scalar(
                select(PaperPortfolioRecord.id).where(PaperPortfolioRecord.active.is_(True))
            )
        report = _build_report(
            experiment,
            portfolio,
            decisions,
            strategy_decisions,
            trades,
            orders,
            risk_assessments,
        )
        report["active_paper_portfolio_id"] = (
            str(active_portfolio_id) if active_portfolio_id else None
        )
        report["report_portfolio_is_active"] = experiment.portfolio_id == active_portfolio_id
        report["portfolio"]["portfolio_id"] = str(experiment.portfolio_id)
        return report


def horizon_coverage(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Missing observations are not flat returns; legacy labels stay unverified."""
    result = {}
    for horizon in (10, 30, 60, 120, 300, 600, 1800, 3600):
        counts = {"observed": 0, "gap": 0, "missing_or_pending": 0, "legacy_unverified": 0}
        for row in rows:
            label = row.get(str(horizon))
            status = (
                "missing_or_pending"
                if label is None
                else label.get("coverage", "legacy_unverified")
            )
            counts[status if status in counts else "legacy_unverified"] += 1
        result[str(horizon)] = counts
    return result


def _build_report(
    experiment: ExperimentRunRecord,
    portfolio: PaperPortfolioRecord | None,
    decisions: list[DecisionOutcomeRecord],
    strategy_decisions: list[StrategyDecisionRecord],
    trades: list[TradeOutcomeRecord],
    orders: list[PaperOrderRecord],
    risk_assessments: list[TokenRiskAssessmentRecord],
) -> dict[str, Any]:
    closed = [item for item in trades if item.status == "closed" and item.realized_pnl is not None]
    wins = [item for item in closed if (item.realized_pnl or Decimal(0)) > 0]
    losses = [item for item in closed if (item.realized_pnl or Decimal(0)) < 0]
    pnls = [item.realized_pnl or Decimal(0) for item in closed]
    total_pnl = sum(pnls, start=Decimal(0))
    gross_profit = sum((value for value in pnls if value > 0), start=Decimal(0))
    gross_loss = abs(sum((value for value in pnls if value < 0), start=Decimal(0)))
    largest_win = max((value for value in pnls if value > 0), default=Decimal(0))
    initial_cash = portfolio.initial_cash if portfolio is not None else Decimal(0)
    max_drawdown, max_drawdown_percent = _maximum_drawdown(initial_cash, pnls)
    rejection_reasons: dict[str, int] = {}
    total_fees = Decimal(0)
    signal_to_decision: list[Decimal] = []
    decision_to_fill: list[Decimal] = []
    signal_to_fill: list[Decimal] = []
    market_data_age: list[Decimal] = []
    for order in orders:
        if order.status == "rejected":
            reason = order.rejection_reason or "unknown"
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        fill = order.fill_json
        if not isinstance(fill, dict):
            continue
        total_fees += _decimal(fill.get("total_fee_portfolio"))
        _append_duration(signal_to_decision, fill, "signal_at", "decision_at")
        _append_duration(decision_to_fill, fill, "decision_at", "filled_at")
        _append_duration(signal_to_fill, fill, "signal_at", "filled_at")
        _append_duration(market_data_age, fill, "market_observed_at", "decision_at")
    score_buckets = {"below_50": 0, "50_59": 0, "60_69": 0, "70_79": 0, "80_plus": 0}
    regime_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    decision_reason_counts: dict[str, int] = {}
    decision_reason_details: dict[str, int] = {}
    for decision in strategy_decisions:
        regime_counts[decision.regime] = regime_counts.get(decision.regime, 0) + 1
        action_counts[decision.action] = action_counts.get(decision.action, 0) + 1
        for reason in decision.reasons:
            detailed_reason = str(reason)
            decision_reason_details[detailed_reason] = (
                decision_reason_details.get(detailed_reason, 0) + 1
            )
            normalized_reason = detailed_reason.split(":", maxsplit=1)[0]
            decision_reason_counts[normalized_reason] = (
                decision_reason_counts.get(normalized_reason, 0) + 1
            )
        score = decision.final_score
        if score is None or score < 50:
            score_buckets["below_50"] += 1
        elif score < 60:
            score_buckets["50_59"] += 1
        elif score < 70:
            score_buckets["60_69"] += 1
        elif score < 80:
            score_buckets["70_79"] += 1
        else:
            score_buckets["80_plus"] += 1
    trade_score_segments = _trade_segments(closed, lambda item: _score_bucket(_trade_score(item)))
    trade_exit_segments = _trade_segments(closed, lambda item: item.exit_reason or "unknown")
    trade_size_segments = _trade_segments(
        closed, lambda item: _position_size_bucket(item.entry_cost_portfolio, initial_cash)
    )
    recent_active_decisions = [
        {
            "decided_at": item.decided_at.isoformat(),
            "action": item.action,
            "score": str(item.final_score) if item.final_score is not None else None,
            "regime": item.regime,
            "reasons": item.reasons,
        }
        for item in sorted(
            strategy_decisions, key=lambda decision: decision.decided_at, reverse=True
        )[:10]
    ]
    critical_unknown_counts: dict[str, int] = {}
    critical_unknown_details: dict[str, int] = {}
    for assessment in risk_assessments:
        for unknown in assessment.critical_unknowns:
            code = str(unknown)
            critical_unknown_counts[code] = critical_unknown_counts.get(code, 0) + 1
        for evidence in assessment.evidence_json:
            if not isinstance(evidence, dict) or evidence.get("availability") != "unknown":
                continue
            detail = f"{evidence.get('code', 'unknown')}:{evidence.get('message', 'unknown')}"
            critical_unknown_details[detail] = critical_unknown_details.get(detail, 0) + 1
    return {
        "experiment": _experiment_payload(experiment),
        "configuration_integrity": (
            "mixed_explicit_revisions"
            if experiment.configuration_snapshot_json.get("configuration_history")
            else "single_configuration"
        ),
        "sizing_periods": _trade_segments(
            closed,
            lambda item: (
                "before_latest_configuration_change"
                if experiment.configuration_snapshot_json.get("configuration_history")
                and (_datetime(item.entry_at.isoformat()) or utc_now())
                < (
                    _datetime(experiment.configuration_snapshot_json.get("captured_at"))
                    or utc_now()
                )
                else "current_configuration"
            ),
        ),
        "portfolio": {
            "initial_cash": str(initial_cash),
            "cash_balance": str(portfolio.cash_balance) if portfolio is not None else None,
            "realized_pnl": str(portfolio.realized_pnl) if portfolio is not None else None,
            "currency": portfolio.currency if portfolio is not None else None,
        },
        "sample": {
            "decisions": len(decisions),
            "active_strategy_decisions": len(strategy_decisions),
            "orders": len(orders),
            "trades": len(trades),
            "open_trades": len(trades) - len(closed),
            "closed_trades": len(closed),
        },
        "performance": {
            "post_exit_coverage": horizon_coverage(
                [(item.post_exit_json or {}).get("horizons", {}) for item in closed]
            ),
            "decision_coverage": horizon_coverage(
                [item.horizon_returns_json or {} for item in decisions]
            ),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_percent": _ratio_percent(len(wins), len(closed)),
            "realized_pnl": str(total_pnl),
            "expectancy_per_trade": str(total_pnl / len(closed)) if closed else None,
            "profit_factor": str(gross_profit / gross_loss) if gross_loss > 0 else None,
            "largest_win": str(largest_win),
            "pnl_excluding_largest_win": str(total_pnl - largest_win),
            "maximum_drawdown": str(max_drawdown),
            "maximum_drawdown_percent": str(max_drawdown_percent),
            "total_execution_fees": str(total_fees),
        },
        "execution": {
            "rejections": sum(rejection_reasons.values()),
            "rejection_reasons": dict(
                sorted(rejection_reasons.items(), key=lambda item: item[1], reverse=True)
            ),
            "latency_ms": {
                "signal_to_decision": _percentile_summary(signal_to_decision),
                "decision_to_fill": _percentile_summary(decision_to_fill),
                "signal_to_fill": _percentile_summary(signal_to_fill),
                "market_data_age_at_decision": _percentile_summary(market_data_age),
            },
        },
        "segments": {
            "decision_score_buckets": score_buckets,
            "decision_actions": action_counts,
            "decision_reasons": dict(
                sorted(
                    decision_reason_counts.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ),
            "decision_reason_details": dict(
                sorted(
                    decision_reason_details.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ),
            "market_regimes": regime_counts,
            "closed_trades_by_score": trade_score_segments,
            "closed_trades_by_exit": trade_exit_segments,
            "closed_trades_by_position_size": trade_size_segments,
            "recent_active_decisions": recent_active_decisions,
            "risk_critical_unknowns": dict(
                sorted(
                    critical_unknown_counts.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ),
            "risk_unknown_details": dict(
                sorted(
                    critical_unknown_details.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ),
        },
    }


def _trade_segments(
    trades: list[TradeOutcomeRecord],
    key_for: Callable[[TradeOutcomeRecord], str],
) -> dict[str, dict[str, str | int | None]]:
    grouped: dict[str, list[TradeOutcomeRecord]] = {}
    for trade in trades:
        grouped.setdefault(str(key_for(trade)), []).append(trade)
    result: dict[str, dict[str, str | int | None]] = {}
    for key, items in sorted(grouped.items()):
        pnls = [item.realized_pnl or Decimal(0) for item in items]
        wins = sum(1 for value in pnls if value > 0)
        gross_profit = sum((value for value in pnls if value > 0), start=Decimal(0))
        gross_loss = abs(sum((value for value in pnls if value < 0), start=Decimal(0)))
        result[key] = {
            "trades": len(items),
            "wins": wins,
            "win_rate_percent": _ratio_percent(wins, len(items)),
            "realized_pnl": str(sum(pnls, start=Decimal(0))),
            "expectancy_per_trade": str(sum(pnls, start=Decimal(0)) / len(items)),
            "profit_factor": str(gross_profit / gross_loss) if gross_loss > 0 else None,
            "average_pnl_percent": str(
                sum((item.pnl_percent or Decimal(0) for item in items), start=Decimal(0))
                / len(items)
            ),
            "average_entry_cost": str(
                sum((item.entry_cost_portfolio for item in items), start=Decimal(0)) / len(items)
            ),
        }
    return result


def _trade_score(trade: TradeOutcomeRecord) -> Decimal | None:
    payload = trade.score_snapshot_json
    if not isinstance(payload, dict):
        return None
    value = payload.get("final_score")
    return Decimal(str(value)) if value is not None else None


def _score_bucket(score: Decimal | None) -> str:
    if score is None:
        return "unknown"
    if score < 50:
        return "below_50"
    if score < 60:
        return "50_59"
    if score < 70:
        return "60_69"
    if score < 80:
        return "70_79"
    return "80_plus"


def _position_size_bucket(cost: Decimal, initial_cash: Decimal) -> str:
    if initial_cash <= 0:
        return "unknown"
    percent = cost / initial_cash * Decimal(100)
    if percent < 5:
        return "below_5_percent"
    if percent < 10:
        return "5_9_percent"
    if percent < 15:
        return "10_14_percent"
    return "15_plus_percent"


def _maximum_drawdown(initial_cash: Decimal, pnls: list[Decimal]) -> tuple[Decimal, Decimal]:
    equity = initial_cash
    peak = initial_cash
    maximum = Decimal(0)
    maximum_percent = Decimal(0)
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        drawdown = peak - equity
        if drawdown > maximum:
            maximum = drawdown
            maximum_percent = drawdown / peak * Decimal(100) if peak > 0 else Decimal(0)
    return maximum, maximum_percent


def _append_duration(
    target: list[Decimal], payload: dict[str, Any], start_key: str, end_key: str
) -> None:
    start = _datetime(payload.get(start_key))
    end = _datetime(payload.get(end_key))
    if start is not None and end is not None and end >= start:
        target.append(Decimal(str((end - start).total_seconds() * 1000)))


def _percentile_summary(values: list[Decimal]) -> dict[str, str | int | None]:
    if not values:
        return {"count": 0, "p50": None, "p95": None, "max": None}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "p50": str(_nearest_rank(ordered, Decimal("0.50"))),
        "p95": str(_nearest_rank(ordered, Decimal("0.95"))),
        "max": str(ordered[-1]),
    }


def _nearest_rank(values: list[Decimal], percentile: Decimal) -> Decimal:
    rank_value = (Decimal(len(values)) * percentile).to_integral_value(rounding="ROUND_CEILING")
    rank = max(1, int(rank_value))
    return values[rank - 1]


def _ratio_percent(numerator: int, denominator: int) -> str | None:
    return str(Decimal(numerator) * Decimal(100) / Decimal(denominator)) if denominator else None


def _decimal(value: object) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal(0)


def _datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _experiment_payload(record: ExperimentRunRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "name": record.name,
        "status": record.status,
        "portfolio_id": str(record.portfolio_id),
        "strategy_key": record.strategy_key,
        "strategy_version_id": str(record.strategy_version_id),
        "application_version": record.application_version,
        "started_at": record.started_at.isoformat(),
        "stopped_at": record.stopped_at.isoformat() if record.stopped_at is not None else None,
        "configuration_snapshot": record.configuration_snapshot_json,
        "notes": record.notes,
    }
