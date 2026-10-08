"""Read-only PAPER history across portfolios, independent of current discovery."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from memebot.core.clock import utc_now

from .models import (
    PaperOrderRecord,
    PaperPortfolioRecord,
    PaperPositionRecord,
    TokenRecord,
    TokenTradeRecord,
)


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

    async def chart_markers(self, address: str, *, limit: int = 10) -> dict[str, Any] | None:
        """Recent paper fills of one Pump token for drawing on an external chart.

        `address` may be the mint or the bonding-curve market (Axiom URLs use the pair).
        Prices are given per whole token and as market cap, in SOL and in USD, because
        terminals display either. Standard Pump tokens: 6 decimals, 1e9 supply.
        """
        async with self.sessions() as session:
            positions = list(
                await session.scalars(
                    select(PaperPositionRecord)
                    .where(
                        (PaperPositionRecord.mint == address)
                        | (PaperPositionRecord.market_address == address)
                    )
                    .order_by(PaperPositionRecord.opened_at.desc())
                    .limit(limit)
                )
            )
            if not positions:
                return None
            mint = positions[0].mint
            orders = list(
                await session.scalars(
                    select(PaperOrderRecord)
                    .where(
                        PaperOrderRecord.mint == mint,
                        PaperOrderRecord.status == "filled",
                        PaperOrderRecord.filled_at >= min(p.opened_at for p in positions),
                    )
                    .order_by(PaperOrderRecord.filled_at)
                )
            )

        def levels(raw: Decimal, sol_usd: Decimal) -> dict[str, float]:
            price_sol = raw * Decimal("0.001")
            return dict(
                price_sol=float(price_sol),
                price_usd=float(price_sol * sol_usd),
                mcap_sol=float(price_sol * 1_000_000_000),
                mcap_usd=float(price_sol * 1_000_000_000 * sol_usd),
            )

        fills = []
        sol_usd = Decimal(0)
        latest = positions[0]
        entry_raw: Decimal | None = None
        for order in orders:
            fill = order.fill_json or {}
            if order.filled_at is None or not fill.get("actual_fill_price_raw"):
                continue
            sol_usd = Decimal(str(fill.get("quote_price_in_portfolio_currency") or 0))
            if order.side == "buy" and order.filled_at >= latest.opened_at and entry_raw is None:
                entry_raw = Decimal(str(fill["actual_fill_price_raw"]))
            fills.append(
                dict(
                    time=_epoch(order.filled_at),
                    side=order.side,
                    effect=order.position_effect,
                    reason=order.exit_reason,
                    amount=float(Decimal(str(fill.get("gross_portfolio_amount") or 0))),
                    sol=float(Decimal(str(fill.get("gross_quote_amount_raw") or 0)) / 10**9),
                    **levels(Decimal(str(fill["actual_fill_price_raw"])), sol_usd),
                )
            )
        open_position = None
        if latest.status == "open" and sol_usd > 0 and entry_raw is not None:
            mark = latest.execution_mark_json or {}
            value = mark.get("net_portfolio_value")
            cost = latest.remaining_cost_basis
            open_position = dict(
                opened=_epoch(latest.opened_at),
                cost=float(cost),
                pnl=float(Decimal(str(value)) - cost) if value is not None else None,
                pnl_percent=float((Decimal(str(value)) / cost - 1) * 100)
                if value is not None and cost > 0
                else None,
                **levels(entry_raw, sol_usd),
            )
        return dict(
            mint=mint,
            realized_pnl=float(sum((p.realized_pnl for p in positions), start=Decimal(0))),
            fills=fills,
            open=open_position,
        )

    async def latest_closed_position_id(self, portfolio_id: str, mint: str) -> str | None:
        async with self.sessions() as session:
            identifier = await session.scalar(
                select(PaperPositionRecord.id)
                .where(
                    PaperPositionRecord.portfolio_id == UUID(portfolio_id),
                    PaperPositionRecord.mint == mint,
                    PaperPositionRecord.status == "closed",
                )
                .order_by(PaperPositionRecord.closed_at.desc())
                .limit(1)
            )
        return str(identifier) if identifier is not None else None

    async def chart(
        self, position_id: str, *, before_seconds: int = 60, after_seconds: int = 60
    ) -> dict[str, Any] | None:
        """Market trades around one position plus its fills, for an entry/exit chart."""
        try:
            identifier = UUID(position_id)
        except ValueError:
            return None
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
            end = position.closed_at or utc_now()
            filters = [
                PaperOrderRecord.portfolio_id == position.portfolio_id,
                PaperOrderRecord.mint == position.mint,
                PaperOrderRecord.status == "filled",
                PaperOrderRecord.filled_at >= position.opened_at,
                PaperOrderRecord.filled_at <= end,
            ]
            orders = list(
                await session.scalars(
                    select(PaperOrderRecord).where(*filters).order_by(PaperOrderRecord.filled_at)
                )
            )
            trades = (
                await session.execute(
                    select(TokenTradeRecord.source_event_at, TokenTradeRecord.price_raw)
                    .where(
                        TokenTradeRecord.token_id == position.token_id,
                        TokenTradeRecord.source_event_at
                        >= position.opened_at - timedelta(seconds=before_seconds),
                        TokenTradeRecord.source_event_at <= end + timedelta(seconds=after_seconds),
                    )
                    .order_by(TokenTradeRecord.source_event_at)
                    .limit(5000)
                )
            ).all()
        fills = []
        for order in orders:
            fill = order.fill_json or {}
            if order.filled_at is None or fill.get("actual_fill_price_raw") is None:
                continue
            fills.append(
                dict(
                    at=order.filled_at,
                    side=order.side,
                    effect=order.position_effect,
                    reason=order.exit_reason,
                    price=Decimal(str(fill["actual_fill_price_raw"])),
                    amount=Decimal(str(fill.get("gross_portfolio_amount") or 0)),
                    fees=Decimal(str(fill.get("total_fee_portfolio") or 0)),
                )
            )
        return dict(
            position=self.position(position, token, portfolio),
            entry_price=position.entry_price_raw,
            fills=fills,
            prices=[(at, price) for at, price in trades if price and price > 0],
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


def _epoch(value: datetime) -> int:
    # SQLite returns naive UTC; PostgreSQL returns aware datetimes.
    return int((value if value.tzinfo else value.replace(tzinfo=UTC)).timestamp())
