"""Read-only AWW position and exit-attempt evidence."""
import asyncio
import json
from collections import Counter
from sqlalchemy import select
from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import PaperOrderRecord, PaperPositionRecord

async def main():
    db = Database(create_database_engine(Settings().database_url))
    try:
        async with db.sessions() as session:
            mint = '9cxR58NxPER4oemD83iVZU9cKH54NdhzbeNfosJkpump'
            position = await session.scalar(select(PaperPositionRecord).where(PaperPositionRecord.mint == mint))
            orders = list(await session.scalars(select(PaperOrderRecord).where(
                PaperOrderRecord.mint == mint).order_by(PaperOrderRecord.created_at)))
            def summary(order):
                fill = order.fill_json or {}
                return dict(at=order.created_at, side=order.side, status=order.status,
                            effect=order.position_effect, reject=order.rejection_reason,
                            exit_reason=order.exit_reason, requested=order.requested_portfolio_amount,
                            quantity=fill.get('token_amount_raw'), gross=fill.get('gross_portfolio_amount'),
                            fees=fill.get('total_fee_portfolio'))
            print(json.dumps(dict(status=position.status, opened_at=position.opened_at,
                closed_at=position.closed_at, realized=position.realized_pnl,
                remaining_basis=position.remaining_cost_basis,
                filled=[summary(order) for order in orders if order.status == 'filled'],
                rejection_counts=dict(Counter(order.rejection_reason for order in orders if order.status != 'filled')),
                first_rejections=[summary(order) for order in orders if order.status != 'filled'][:3],
                latest_orders=[summary(order) for order in orders[-3:]]), default=str, indent=2))
    finally:
        await db.dispose()

asyncio.run(main())
