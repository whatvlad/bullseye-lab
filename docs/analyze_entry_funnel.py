"""Read-only summary of recent discovery-to-paper-entry decisions."""

import asyncio
import json
from collections import Counter
from datetime import timedelta

from sqlalchemy import select

from memebot.core.clock import utc_now
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import (
    PaperOrderRecord,
    StrategyDecisionRecord,
    TokenRiskAssessmentRecord,
)


async def main() -> None:
    db = Database(create_database_engine(Settings().database_url))
    since = utc_now() - timedelta(hours=48)
    try:
        async with db.sessions() as session:
            decisions = (
                await session.scalars(
                    select(StrategyDecisionRecord)
                    .where(StrategyDecisionRecord.decided_at >= since)
                    .order_by(StrategyDecisionRecord.decided_at.desc())
                )
            ).all()
            orders = (
                await session.scalars(
                    select(PaperOrderRecord)
                    .where(PaperOrderRecord.created_at >= since)
                    .order_by(PaperOrderRecord.created_at.desc())
                )
            ).all()
            risks = (
                await session.scalars(
                    select(TokenRiskAssessmentRecord)
                    .where(TokenRiskAssessmentRecord.assessed_at >= since)
                    .order_by(TokenRiskAssessmentRecord.assessed_at.desc())
                )
            ).all()
        print(
            json.dumps(
                {
                    "since": since.isoformat(),
                    "decisions": len(decisions),
                    "latest_decision": decisions[0].decided_at.isoformat() if decisions else None,
                    "decision_actions": {
                        f"{key}:{action}": count
                        for (key, action), count in Counter(
                            (d.strategy_key, d.action) for d in decisions
                        ).items()
                    },
                    "active_reasons": Counter(
                        reason for d in decisions if d.active_strategy for reason in d.reasons
                    ).most_common(20),
                    "aggressive_reasons": Counter(
                        reason
                        for d in decisions
                        if d.strategy_key == "aggressive"
                        for reason in d.reasons
                    ).most_common(20),
                    "risk_assessments": len(risks),
                    "risk_allowed": dict(Counter(str(r.allowed) for r in risks)),
                    "risk_reasons": Counter(
                        reason for r in risks for reason in r.hard_reject_reasons
                    ).most_common(12),
                    "buy_orders": dict(Counter(o.status for o in orders if o.side == "buy")),
                    "buy_rejections": Counter(
                        o.rejection_reason
                        for o in orders
                        if o.side == "buy" and o.status == "rejected"
                    ).most_common(20),
                    "latest_order": orders[0].created_at.isoformat() if orders else None,
                },
                indent=2,
                default=str,
            )
        )
    finally:
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
