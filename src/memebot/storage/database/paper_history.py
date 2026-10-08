"""Read-only PAPER history across portfolios, independent of current discovery."""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import PaperOrderRecord, PaperPortfolioRecord, PaperPositionRecord, TokenRecord


class PaperHistoryRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def page(self, page: int = 0) -> dict[str, Any]:
        size = 4
        async with self.sessions() as session:
            total = int(
                await session.scalar(select(func.count()).select_from(PaperPositionRecord)) or 0
            )
            pages = max(1, (total + size - 1) // size)
            page = max(0, min(page, pages - 1))
            rows = (
                await session.execute(
                    select(PaperPositionRecord, TokenRecord, PaperPortfolioRecord)
                    .join(TokenRecord, TokenRecord.id == PaperPositionRecord.token_id)
                    .join(
                        PaperPortfolioRecord,
                        PaperPortfolioRecord.id == PaperPositionRecord.portfolio_id,
                    )
                    .order_by(PaperPositionRecord.opened_at.desc(), PaperPositionRecord.id.desc())
                    .offset(page * size)
                    .limit(size)
                )
            ).all()
            items = [
                self.position(position, token, portfolio) for position, token, portfolio in rows
            ]
            totals = (
                await session.execute(
                    select(
                        PaperPortfolioRecord.currency, func.sum(PaperPositionRecord.realized_pnl)
                    )
                    .join(
                        PaperPositionRecord,
                        PaperPositionRecord.portfolio_id == PaperPortfolioRecord.id,
                    )
                    .group_by(PaperPortfolioRecord.currency)
                )
            ).all()
        return dict(
            page=page,
            pages=pages,
            total=total,
            items=items,
            realized_by_currency={currency: str(value) for currency, value in totals},
        )

    async def detail(self, position_id: str, page: int = 0) -> dict[str, Any] | None:
        try:
            identifier = UUID(position_id)
        except ValueError:
            return None
        size = 5
        async with self.sessions() as session:
            row = (
                await session.execute(
                    select(PaperPositionRecord, TokenRecord, PaperPortfolioRecord)
                    .join(TokenRecord, TokenRecord.id == PaperPositionRecord.token_id)
                    .join(
                        PaperPortfolioRecord,
                        PaperPortfolioRecord.id == PaperPositionRecord.portfolio_id,
                    )
                    .where(PaperPositionRecord.id == identifier)
                )
            ).first()
            if row is None:
                return None
            position, token, portfolio = row
            # Fill time binds repeated entries in the same mint to the correct position.
            filters = [
                PaperOrderRecord.portfolio_id == position.portfolio_id,
                PaperOrderRecord.mint == position.mint,
                PaperOrderRecord.status == "filled",
                PaperOrderRecord.filled_at >= position.opened_at,
            ]
            if position.closed_at:
                filters.append(PaperOrderRecord.filled_at <= position.closed_at)
            total = int(
                await session.scalar(
                    select(func.count()).select_from(PaperOrderRecord).where(*filters)
                )
                or 0
            )
            pages = max(1, (total + size - 1) // size)
            page = max(0, min(page, pages - 1))
            orders = list(
                await session.scalars(
                    select(PaperOrderRecord)
                    .where(*filters)
                    .order_by(PaperOrderRecord.filled_at, PaperOrderRecord.event_id)
                    .offset(page * size)
                    .limit(size)
                )
            )
            return dict(
                position=self.position(position, token, portfolio),
                page=page,
                pages=pages,
                total=total,
                orders=[self.order(order) for order in orders],
            )

    @staticmethod
    def position(
        position: PaperPositionRecord, token: TokenRecord, portfolio: PaperPortfolioRecord
    ) -> dict[str, Any]:
        return dict(
            id=str(position.id),
            mint=position.mint,
            name=token.name,
            symbol=token.symbol,
            portfolio=portfolio.name,
            currency=portfolio.currency,
            status=position.status,
            opened_at=position.opened_at.isoformat(),
            closed_at=position.closed_at.isoformat() if position.closed_at else None,
            realized_pnl=str(position.realized_pnl),
            remaining_cost_basis=str(position.remaining_cost_basis),
            partial_take_profit_taken=position.partial_take_profit_taken,
        )

    @staticmethod
    def order(order: PaperOrderRecord) -> dict[str, Any]:
        fill = order.fill_json or {}
        return dict(
            event_id=str(order.event_id),
            at=(order.filled_at or order.created_at).isoformat(),
            side=order.side,
            status=order.status,
            effect=order.position_effect,
            reason=order.exit_reason or order.rejection_reason,
            amount=fill.get("gross_portfolio_amount"),
            fees=fill.get("total_fee_portfolio"),
            price_source=fill.get("price_source"),
        )

    async def csv(self) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "portfolio",
                "currency",
                "coin_name",
                "symbol",
                "mint",
                "time_utc",
                "side",
                "status",
                "position_effect",
                "gross_amount",
                "fees",
                "reason",
                "price_source",
                "event_id",
            ]
        )
        async with self.sessions() as session:
            stream = await session.stream(
                select(PaperOrderRecord, TokenRecord, PaperPortfolioRecord)
                .join(TokenRecord, TokenRecord.id == PaperOrderRecord.token_id)
                .join(
                    PaperPortfolioRecord, PaperPortfolioRecord.id == PaperOrderRecord.portfolio_id
                )
                .order_by(PaperOrderRecord.created_at, PaperOrderRecord.event_id)
                .execution_options(yield_per=500)
            )
            async for order, token, portfolio in stream:
                item = self.order(order)
                cells = [
                    portfolio.name,
                    portfolio.currency,
                    token.name,
                    token.symbol,
                    order.mint,
                    item["at"],
                    item["side"],
                    item["status"],
                    item["effect"],
                    item["amount"],
                    item["fees"],
                    item["reason"],
                    item["price_source"],
                    item["event_id"],
                ]
                # Untrusted coin names must not execute spreadsheet formulas on export.
                writer.writerow(
                    [
                        "'" + value
                        if isinstance(value, str)
                        and value.lstrip().startswith(("=", "+", "-", "@"))
                        else value
                        for value in cells
                    ]
                )
        return ("\ufeff" + output.getvalue()).encode("utf-8")

    async def archive(self) -> bytes:
        positions = io.StringIO(newline="")
        writer = csv.writer(positions)
        writer.writerow(
            [
                "position_id",
                "portfolio",
                "currency",
                "coin_name",
                "symbol",
                "mint",
                "status",
                "opened_at_utc",
                "closed_at_utc",
                "realized_pnl",
                "remaining_cost_basis",
            ]
        )
        async with self.sessions() as session:
            stream = await session.stream(
                select(PaperPositionRecord, TokenRecord, PaperPortfolioRecord)
                .join(TokenRecord, TokenRecord.id == PaperPositionRecord.token_id)
                .join(
                    PaperPortfolioRecord,
                    PaperPortfolioRecord.id == PaperPositionRecord.portfolio_id,
                )
                .order_by(PaperPositionRecord.opened_at, PaperPositionRecord.id)
                .execution_options(yield_per=500)
            )
            async for position, token, portfolio in stream:
                item = self.position(position, token, portfolio)
                name = str(item["name"] or "")
                symbol = str(item["symbol"] or "")
                if name.lstrip().startswith(("=", "+", "-", "@")):
                    name = "'" + name
                if symbol.lstrip().startswith(("=", "+", "-", "@")):
                    symbol = "'" + symbol
                writer.writerow(
                    [
                        item["id"],
                        item["portfolio"],
                        item["currency"],
                        name,
                        symbol,
                        item["mint"],
                        item["status"],
                        item["opened_at"],
                        item["closed_at"],
                        item["realized_pnl"],
                        item["remaining_cost_basis"],
                    ]
                )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("positions.csv", ("\ufeff" + positions.getvalue()).encode("utf-8"))
            archive.writestr("orders.csv", await self.csv())
        return buffer.getvalue()
