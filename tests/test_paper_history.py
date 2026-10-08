import csv
import io
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from memebot.storage.database.engine import Database, create_database_engine
from memebot.storage.database.models import (
    DomainEventRecord,
    PaperOrderRecord,
    PaperPortfolioRecord,
    PaperPositionRecord,
    TokenRecord,
)
from memebot.storage.database.paper_history import PaperHistoryRepository
from memebot.telegram.history import detail_keyboard, detail_view, history_keyboard, history_view


@pytest.mark.asyncio
async def test_all_portfolios_pagination_reentry_and_full_export():
    db = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await db.create_schema_for_tests()
    at = datetime(2026, 10, 3, tzinfo=UTC)
    ids = []
    try:
        async with db.sessions() as session, session.begin():
            token = TokenRecord(
                id=uuid4(),
                mint="So11111111111111111111111111111111111111112",
                name="=Untrusted Coin",
                symbol="AWW",
            )
            session.add(token)
            for cohort in range(2):
                portfolio = PaperPortfolioRecord(
                    id=uuid4(),
                    name=f"Run {cohort}",
                    currency="USDT",
                    initial_cash=Decimal(1000),
                    cash_balance=Decimal(1000),
                    active=cohort == 1,
                )
                session.add(portfolio)
                for trade in range(3):
                    opened = at + timedelta(hours=cohort * 5 + trade)
                    closed = opened + timedelta(minutes=5)
                    position = PaperPositionRecord(
                        id=uuid4(),
                        portfolio_id=portfolio.id,
                        token_id=token.id,
                        mint=token.mint,
                        strategy_key="aggressive",
                        market_address=token.mint,
                        venue="pump_fun",
                        lifecycle="bonding_curve",
                        status="closed",
                        token_quantity_raw=0,
                        remaining_cost_basis=0,
                        realized_pnl=Decimal(3),
                        entry_price_raw=1,
                        peak_price_raw=1,
                        last_price_raw=1,
                        opened_at=opened,
                        closed_at=closed,
                        partial_take_profit_taken=True,
                    )
                    session.add(position)
                    ids.append(str(position.id))
                    for _n, (side, effect, time) in enumerate(
                        [
                            ("buy", "open", opened),
                            ("sell", "partial_close", opened + timedelta(minutes=2)),
                            ("sell", "close", closed),
                        ]
                    ):
                        identifier = uuid4()
                        session.add(
                            DomainEventRecord(
                                event_id=identifier,
                                event_type="paper_order_completed",
                                schema_version=1,
                                provider="test",
                                source_event_at=time,
                                ingested_at=time,
                                payload={},
                            )
                        )
                        session.add(
                            PaperOrderRecord(
                                event_id=identifier,
                                portfolio_id=portfolio.id,
                                token_id=token.id,
                                mint=token.mint,
                                trigger_event_id=identifier,
                                strategy_key="aggressive",
                                side=side,
                                status="filled",
                                position_effect=effect,
                                venue="pump_fun",
                                lifecycle="bonding_curve",
                                requested_portfolio_amount=10,
                                filled_at=time,
                                created_at=time + timedelta(seconds=1),
                                fill_json={
                                    "gross_portfolio_amount": "10",
                                    "total_fee_portfolio": "1",
                                },
                            )
                        )
        repo = PaperHistoryRepository(db.sessions)
        first, last = await repo.page(), await repo.page(999)
        assert first["total"] == 6 and first["pages"] == 2 and last["page"] == 1
        assert len(first["items"]) == 4 and len(last["items"]) == 2
        assert set(item["id"] for item in first["items"]).isdisjoint(
            item["id"] for item in last["items"]
        )
        assert first["realized_by_currency"] == {"USDT": "18.00000000"}
        detail = await repo.detail(ids[0])
        assert detail["total"] == 3  # Reentries in this mint must not bleed into its timeline.
        assert [order["effect"] for order in detail["orders"]] == ["open", "partial_close", "close"]
        text = detail_view(detail)
        assert "=Untrusted Coin" in text and detail["position"]["mint"] in text
        assert "ЧАСТИЧНАЯ ПРОДАЖА" in text and "+3.00 USDT" in text
        assert "solscan.io/token/" in text and "dexscreener.com/solana/" in text
        assert len(history_view(first)) < 4096 and len(text) < 4096
        for keyboard in (history_keyboard(first), detail_keyboard(detail)):
            assert all(
                len(button.callback_data.encode()) <= 64
                for row in keyboard.inline_keyboard
                for button in row
                if button.callback_data
            )
        rows = list(csv.DictReader(io.StringIO((await repo.csv()).decode("utf-8-sig"))))
        assert len(rows) == 18 and {row["portfolio"] for row in rows} == {"Run 0", "Run 1"}
        assert all(row["mint"] == detail["position"]["mint"] for row in rows)
        assert all(row["coin_name"] == "'=Untrusted Coin" for row in rows)
        with zipfile.ZipFile(io.BytesIO(await repo.archive())) as exported:
            position_rows = list(
                csv.DictReader(io.StringIO(exported.read("positions.csv").decode("utf-8-sig")))
            )
            assert len(position_rows) == 6
            assert sum(Decimal(row["realized_pnl"]) for row in position_rows) == 18
            assert exported.read("orders.csv").decode("utf-8-sig").startswith("portfolio,")
        assert await repo.detail("invalid-id") is None
    finally:
        await db.dispose()
