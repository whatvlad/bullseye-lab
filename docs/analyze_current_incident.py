"""Read-only concise paper incident report without credentials or RPC calls."""

import asyncio
import json
from collections import Counter
from decimal import Decimal
from itertools import pairwise

from sqlalchemy import select

from memebot.core.config import Settings
from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.experiments import ExperimentRepository
from memebot.storage.database.models import (
    PaperOrderRecord,
    TokenTradeRecord,
    TradeOutcomeRecord,
    TradingControlRecord,
)


async def main() -> None:
    db = Database(create_database_engine(Settings().database_url))
    try:
        report = await ExperimentRepository(db.sessions).report()
        portfolio_id = report["experiment"]["portfolio_id"]
        async with db.sessions() as session:
            control = await session.get(TradingControlRecord, 1)
            trades = (await session.scalars(
                select(TradeOutcomeRecord)
                .where(TradeOutcomeRecord.portfolio_id == portfolio_id)
                .order_by(TradeOutcomeRecord.entry_at)
            )).all()
            orders = (await session.scalars(
                select(PaperOrderRecord)
                .where(PaperOrderRecord.portfolio_id == portfolio_id)
            )).all()
        filled = [order for order in orders if order.status == "filled"]
        market_gaps = {}
        async with db.sessions() as session:
            for trade in trades:
                stamps = list((await session.scalars(
                    select(TokenTradeRecord.source_event_at)
                    .where(
                        TokenTradeRecord.token_id == trade.token_id,
                        TokenTradeRecord.source_event_at >= trade.entry_at,
                        TokenTradeRecord.source_event_at <= trade.exit_at,
                    )
                    .order_by(TokenTradeRecord.source_event_at)
                )).all()) if trade.exit_at else []
                gaps = [
                    (right - left).total_seconds()
                    for left, right in pairwise(stamps)
                ]
                market_gaps[trade.position_id] = {
                    "observed_trades": len(stamps),
                    "largest_gap_seconds": max(gaps, default=None),
                    "last_trade_before_exit_seconds": (
                        (trade.exit_at - stamps[-1]).total_seconds() if stamps else None
                    ),
                }
        total_fees = sum(
            (Decimal(str((order.fill_json or {}).get("total_fee_portfolio") or 0))
             for order in filled),
            Decimal(0),
        )
        print(json.dumps({
            "portfolio": report["portfolio"],
            "control": {
                "entries_paused": control.entries_paused if control else None,
                "updated_at": control.updated_at.isoformat() if control else None,
                "updated_by_telegram_user_id": (
                    control.updated_by_telegram_user_id if control else None
                ),
            },
            "performance": {
                key: value for key, value in report["performance"].items()
                if key not in {"post_exit_coverage", "decision_coverage"}
            },
            "exit_segments": report["segments"]["closed_trades_by_exit"],
            "size_segments": report["segments"]["closed_trades_by_position_size"],
            "sizing_periods": report["sizing_periods"],
            "order_counts": {
                f"{side}:{status}": count for (side, status), count in
                Counter((order.side, order.status) for order in orders).items()
            },
            "buy_rejections": Counter(
                order.rejection_reason for order in orders
                if order.side == "buy" and order.status == "rejected"
            ).most_common(15),
            "total_fill_fees": str(total_fees),
            "trades": [{
                "mint": trade.mint,
                "entry_at": trade.entry_at.isoformat(),
                "exit_at": trade.exit_at.isoformat() if trade.exit_at else None,
                "entry_cost": str(trade.entry_cost_portfolio),
                "entry_fee": str(trade.entry_fees_portfolio),
                "pnl": str(trade.realized_pnl),
                "pnl_percent": str(trade.pnl_percent),
                "mfe_percent": str(trade.mfe_percent),
                "mae_percent": str(trade.mae_percent),
                "holding_seconds": trade.holding_seconds,
                "exit_reason": trade.exit_reason,
                "score": (trade.score_snapshot_json or {}).get("final_score"),
                "market_observation": market_gaps[trade.position_id],
                "rejected_sells": [
                    {
                        "at": order.created_at.isoformat(),
                        "reason": order.rejection_reason,
                    }
                    for order in orders
                    if order.mint == trade.mint
                    and order.side == "sell"
                    and order.status == "rejected"
                    and order.created_at >= trade.entry_at
                    and (trade.exit_at is None or order.created_at <= trade.exit_at)
                ],
                "fills": [
                    {
                        "side": order.side,
                        "effect": order.position_effect,
                        "gross": (order.fill_json or {}).get("gross_portfolio_amount"),
                        "fee": (order.fill_json or {}).get("total_fee_portfolio"),
                        "impact_bps": (order.fill_json or {}).get("price_impact_bps"),
                        "price_deviation_bps": (
                            order.fill_json or {}
                        ).get("total_price_deviation_bps"),
                    }
                    for order in orders
                    if order.mint == trade.mint and order.status == "filled"
                ],
            } for trade in trades],
        }, indent=2, default=str))
    finally:
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
