from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from memebot.core.clock import utc_now
from memebot.events.models import StrategyDecisionCreated, parse_core_event

from .models import DomainEventRecord, PendingPaperActionRecord


@dataclass(frozen=True, slots=True)
class PendingPaperAction:
    id: UUID
    portfolio_id: UUID
    mint: str
    action: str
    expires_at: datetime
    decision: StrategyDecisionCreated | None
    requested_by_user_id: int | None
    is_new: bool = False


@dataclass(frozen=True, slots=True)
class ExpiredPaperAction:
    id: UUID
    portfolio_id: UUID
    mint: str
    action: str
    decision_event_id: UUID | None
    requested_by_user_id: int | None


class PendingPaperActionRepository:
    """Cross-process coordination for paper actions awaiting a fresh trade."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def enqueue(
        self,
        *,
        portfolio_id: UUID,
        mint: str,
        action: str,
        ttl_seconds: int,
        decision_event_id: UUID | None = None,
        requested_by_user_id: int | None = None,
    ) -> PendingPaperAction:
        now = utc_now()
        async with self._sessions() as session, session.begin():
            record = await session.scalar(
                select(PendingPaperActionRecord).where(
                    PendingPaperActionRecord.portfolio_id == portfolio_id,
                    PendingPaperActionRecord.mint == mint,
                    PendingPaperActionRecord.action == action,
                    PendingPaperActionRecord.status == "pending",
                )
            )
            is_new = record is None
            if record is None:
                record = PendingPaperActionRecord(
                    portfolio_id=portfolio_id,
                    mint=mint,
                    action=action,
                    status="pending",
                    decision_event_id=decision_event_id,
                    requested_by_user_id=requested_by_user_id,
                    expires_at=now + timedelta(seconds=ttl_seconds),
                    reason="waiting_for_fresh_market",
                )
                session.add(record)
            else:
                # Repeated strategy evaluations must not keep extending one wait forever.
                # The first signal owns the fixed deadline and notification.
                pass
            await session.flush()
            return await self._snapshot(session, record, is_new=is_new)

    async def pending_for_mint(self, mint: str, *, action: str) -> PendingPaperAction | None:
        now = utc_now()
        async with self._sessions() as session, session.begin():
            record = await session.scalar(
                select(PendingPaperActionRecord)
                .where(
                    PendingPaperActionRecord.mint == mint,
                    PendingPaperActionRecord.action == action,
                    PendingPaperActionRecord.status == "pending",
                )
                .order_by(PendingPaperActionRecord.created_at)
                .limit(1)
            )
            if record is None:
                return None
            if _as_utc(record.expires_at) < now:
                # The sweeper owns the state transition and final notification.
                return None
            record.last_attempt_at = now
            return await self._snapshot(session, record)

    async def finish(
        self,
        action_id: UUID,
        *,
        status: str,
        reason: str,
        completion_event_id: UUID | None = None,
    ) -> None:
        async with self._sessions() as session, session.begin():
            record = await session.get(PendingPaperActionRecord, action_id)
            if record is None or record.status != "pending":
                return
            record.status = status
            record.reason = reason
            record.completion_event_id = completion_event_id
            record.completed_at = utc_now()

    async def expire_due(self) -> tuple[ExpiredPaperAction, ...]:
        """Atomically expire waits so the worker can emit one final status event."""
        now = utc_now()
        async with self._sessions() as session, session.begin():
            records = (
                await session.scalars(
                    select(PendingPaperActionRecord).where(
                        PendingPaperActionRecord.status == "pending",
                        PendingPaperActionRecord.expires_at < now,
                    )
                )
            ).all()
            expired: list[ExpiredPaperAction] = []
            for record in records:
                record.status = "expired"
                record.completed_at = now
                record.reason = "fresh_market_timeout"
                expired.append(
                    ExpiredPaperAction(
                        id=record.id,
                        portfolio_id=record.portfolio_id,
                        mint=record.mint,
                        action=record.action,
                        decision_event_id=record.decision_event_id,
                        requested_by_user_id=record.requested_by_user_id,
                    )
                )
            return tuple(expired)

    async def cancel_manual_close(self, portfolio_id: UUID, mint: str) -> None:
        async with self._sessions() as session, session.begin():
            records = (
                await session.scalars(
                    select(PendingPaperActionRecord).where(
                        PendingPaperActionRecord.portfolio_id == portfolio_id,
                        PendingPaperActionRecord.mint == mint,
                        PendingPaperActionRecord.action == "manual_close",
                        PendingPaperActionRecord.status == "pending",
                    )
                )
            ).all()
            now = utc_now()
            for record in records:
                record.status = "cancelled"
                record.reason = "operator_force_close"
                record.completed_at = now

    @staticmethod
    async def _snapshot(
        session: AsyncSession,
        record: PendingPaperActionRecord,
        *,
        is_new: bool = False,
    ) -> PendingPaperAction:
        decision: StrategyDecisionCreated | None = None
        if record.decision_event_id is not None:
            stored = await session.get(DomainEventRecord, record.decision_event_id)
            if stored is not None:
                parsed = parse_core_event(stored.payload)
                if isinstance(parsed, StrategyDecisionCreated):
                    decision = parsed
        return PendingPaperAction(
            id=record.id,
            portfolio_id=record.portfolio_id,
            mint=record.mint,
            action=record.action,
            expires_at=_as_utc(record.expires_at),
            decision=decision,
            requested_by_user_id=record.requested_by_user_id,
            is_new=is_new,
        )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
