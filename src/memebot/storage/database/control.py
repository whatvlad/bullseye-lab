from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from memebot.models.common import is_solana_address
from memebot.storage.database.models import (
    PaperOrderRecord,
    StrategyConfigurationRecord,
    StrategyDecisionRecord,
    TokenControlRecord,
    TokenRecord,
    TradingControlRecord,
)


@dataclass(frozen=True, slots=True)
class TradingControlSnapshot:
    entries_paused: bool
    active_strategy_key: str
    base_position_percent: Decimal
    max_position_percent: Decimal
    max_open_positions: int
    stop_loss_percent: Decimal
    take_profit_percent: Decimal
    trailing_stop_percent: Decimal
    max_holding_seconds: int


class ControlRepository:
    """Persistent cross-process control state for the worker and Telegram UI."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def ensure(
        self,
        *,
        active_strategy_key: str,
        base_position_percent: Decimal,
        max_position_percent: Decimal,
        max_open_positions: int,
        stop_loss_percent: Decimal,
        take_profit_percent: Decimal,
        trailing_stop_percent: Decimal,
        max_holding_seconds: int,
    ) -> TradingControlSnapshot:
        async with self._sessions() as session, session.begin():
            record = await session.get(TradingControlRecord, 1)
            if record is None:
                record = TradingControlRecord(
                    id=1,
                    entries_paused=False,
                    active_strategy_key=active_strategy_key,
                    base_position_percent=base_position_percent,
                    max_position_percent=max_position_percent,
                    max_open_positions=max_open_positions,
                    stop_loss_percent=stop_loss_percent,
                    take_profit_percent=take_profit_percent,
                    trailing_stop_percent=trailing_stop_percent,
                    max_holding_seconds=max_holding_seconds,
                )
                session.add(record)
                await session.flush()
            return _snapshot(record)

    async def get(self) -> TradingControlSnapshot | None:
        async with self._sessions() as session:
            record = await session.get(TradingControlRecord, 1)
            return _snapshot(record) if record is not None else None

    async def set_paused(self, paused: bool, *, user_id: int) -> TradingControlSnapshot:
        async with self._sessions() as session, session.begin():
            record = await _required_control(session)
            record.entries_paused = paused
            record.updated_by_telegram_user_id = user_id
            await session.flush()
            return _snapshot(record)

    async def pause_for_provider_halt(self) -> tuple[TradingControlSnapshot, bool]:
        """Fail closed without impersonating a Telegram operator."""
        return await self.pause_automatically()

    async def pause_automatically(self) -> tuple[TradingControlSnapshot, bool]:
        """Pause entries for a system safety condition without operator attribution."""
        async with self._sessions() as session, session.begin():
            record = await _required_control(session)
            changed = not record.entries_paused
            record.entries_paused = True
            record.updated_by_telegram_user_id = None
            await session.flush()
            return _snapshot(record), changed

    async def set_active_strategy(
        self, strategy_key: str, *, user_id: int
    ) -> TradingControlSnapshot:
        async with self._sessions() as session, session.begin():
            available = await session.scalar(
                select(func.count())
                .select_from(StrategyConfigurationRecord)
                .where(
                    StrategyConfigurationRecord.strategy_key == strategy_key,
                    StrategyConfigurationRecord.enabled.is_(True),
                )
            )
            if not available:
                raise ValueError("unknown_or_disabled_strategy")
            record = await _required_control(session)
            record.active_strategy_key = strategy_key
            record.updated_by_telegram_user_id = user_id
            await session.flush()
            return _snapshot(record)

    async def update_risk(
        self,
        *,
        stop_loss_percent: Decimal | None = None,
        take_profit_percent: Decimal | None = None,
        trailing_stop_percent: Decimal | None = None,
        max_open_positions: int | None = None,
        user_id: int,
    ) -> TradingControlSnapshot:
        async with self._sessions() as session, session.begin():
            record = await _required_control(session)
            if stop_loss_percent is not None:
                _percent(stop_loss_percent, "stop_loss_percent")
                record.stop_loss_percent = stop_loss_percent
            if take_profit_percent is not None:
                _positive(take_profit_percent, "take_profit_percent")
                record.take_profit_percent = take_profit_percent
            if trailing_stop_percent is not None:
                _percent(trailing_stop_percent, "trailing_stop_percent")
                record.trailing_stop_percent = trailing_stop_percent
            if max_open_positions is not None:
                if not 1 <= max_open_positions <= 1000:
                    raise ValueError("max_open_positions_out_of_range")
                record.max_open_positions = max_open_positions
            record.updated_by_telegram_user_id = user_id
            await session.flush()
            return _snapshot(record)

    async def update_sizing(
        self,
        *,
        base_position_percent: Decimal,
        max_position_percent: Decimal,
        user_id: int,
    ) -> TradingControlSnapshot:
        _percent(base_position_percent, "base_position_percent")
        _percent(max_position_percent, "max_position_percent")
        if base_position_percent > max_position_percent:
            raise ValueError("base_position_exceeds_maximum")
        async with self._sessions() as session, session.begin():
            record = await _required_control(session)
            record.base_position_percent = base_position_percent
            record.max_position_percent = max_position_percent
            record.updated_by_telegram_user_id = user_id
            await session.flush()
            return _snapshot(record)

    async def set_token_control(
        self,
        mint: str,
        *,
        watchlisted: bool | None = None,
        blacklisted: bool | None = None,
        reason: str | None = None,
        user_id: int,
    ) -> None:
        if not is_solana_address(mint):
            raise ValueError("invalid_solana_mint")
        async with self._sessions() as session, session.begin():
            record = await session.get(TokenControlRecord, mint)
            if record is None:
                record = TokenControlRecord(mint=mint)
                session.add(record)
            if watchlisted is not None:
                record.watchlisted = watchlisted
            if blacklisted is not None:
                record.blacklisted = blacklisted
            record.reason = reason[:256] if reason else None
            record.updated_by_telegram_user_id = user_id

    async def is_blacklisted(self, mint: str) -> bool:
        async with self._sessions() as session:
            value = await session.scalar(
                select(TokenControlRecord.blacklisted).where(TokenControlRecord.mint == mint)
            )
            return bool(value)

    async def token_controls(self, *, kind: str) -> list[dict[str, Any]]:
        if kind not in {"watchlist", "blacklist"}:
            raise ValueError("unknown_token_control_kind")
        flag = (
            TokenControlRecord.watchlisted
            if kind == "watchlist"
            else TokenControlRecord.blacklisted
        )
        async with self._sessions() as session:
            records = (
                await session.scalars(
                    select(TokenControlRecord)
                    .where(flag.is_(True))
                    .order_by(TokenControlRecord.updated_at.desc())
                )
            ).all()
            return [
                {
                    "mint": item.mint,
                    "reason": item.reason,
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in records
            ]

    async def latest_signals(self, *, limit: int = 10) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(StrategyDecisionRecord, TokenRecord)
                    .join(TokenRecord, TokenRecord.id == StrategyDecisionRecord.token_id)
                    .where(StrategyDecisionRecord.action.in_(("enter_candidate", "watch")))
                    .order_by(StrategyDecisionRecord.decided_at.desc())
                    .limit(limit)
                )
            ).all()
            return [
                {
                    "mint": token.mint,
                    "symbol": token.symbol,
                    "strategy": decision.strategy_key,
                    "action": decision.action,
                    "score": (
                        str(decision.final_score) if decision.final_score is not None else None
                    ),
                    "regime": decision.regime,
                    "decided_at": decision.decided_at.isoformat(),
                }
                for decision, token in rows
            ]

    async def strategy_comparison(self) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            decision_rows = (
                await session.execute(
                    select(
                        StrategyDecisionRecord.strategy_key,
                        func.count(StrategyDecisionRecord.event_id),
                        func.sum(
                            func.cast(StrategyDecisionRecord.action == "enter_candidate", Integer)
                        ),
                    ).group_by(StrategyDecisionRecord.strategy_key)
                )
            ).all()
            fill_rows = (
                await session.execute(
                    select(PaperOrderRecord.strategy_key, func.count(PaperOrderRecord.event_id))
                    .where(PaperOrderRecord.status == "filled")
                    .group_by(PaperOrderRecord.strategy_key)
                )
            ).all()
            fills: dict[str, int] = {key: int(count) for key, count in fill_rows}
            return [
                {
                    "strategy": key,
                    "decisions": int(decisions),
                    "entry_candidates": int(entries or 0),
                    "fills": int(fills.get(key, 0)),
                }
                for key, decisions, entries in sorted(decision_rows)
            ]


async def _required_control(session: AsyncSession) -> TradingControlRecord:
    record = await session.get(TradingControlRecord, 1)
    if record is None:
        raise RuntimeError("trading_control_not_initialized")
    return record


def _snapshot(record: TradingControlRecord) -> TradingControlSnapshot:
    return TradingControlSnapshot(
        entries_paused=record.entries_paused,
        active_strategy_key=record.active_strategy_key,
        base_position_percent=record.base_position_percent,
        max_position_percent=record.max_position_percent,
        max_open_positions=record.max_open_positions,
        stop_loss_percent=record.stop_loss_percent,
        take_profit_percent=record.take_profit_percent,
        trailing_stop_percent=record.trailing_stop_percent,
        max_holding_seconds=record.max_holding_seconds,
    )


def _positive(value: Decimal, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name}_must_be_positive")


def _percent(value: Decimal, name: str) -> None:
    if value <= 0 or value > 100:
        raise ValueError(f"{name}_out_of_range")
