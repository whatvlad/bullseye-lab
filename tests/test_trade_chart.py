import asyncio
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
    TokenTradeRecord,
)
from memebot.storage.database.paper_history import PaperHistoryRepository
from memebot.telegram.charts import chart_caption, render_chart_png, trade_summary
from memebot.telegram.notifications import TelegramTradeNotifier

AT = datetime(2026, 10, 8, 17, 57, tzinfo=UTC)
MINT = "4BJ8E6sq4YL3Yeua3FiPtDrRkRdn3kPa7E5QQYEDpump"


def _data():
    prices = [(AT + timedelta(seconds=s), Decimal(p)) for s, p in ((-30, "0.9"), (0, "1"))]
    prices += [(AT + timedelta(seconds=10 * i), Decimal("1") + Decimal(i) / 10) for i in (1, 5)]
    prices += [(AT + timedelta(seconds=120), Decimal("0.6"))]
    return dict(
        position=dict(
            id="p",
            mint=MINT,
            name="SuperIntelligence Fund",
            symbol="SIF",
            currency="USDT",
            status="closed",
            opened_at=AT.isoformat(),
            closed_at=(AT + timedelta(seconds=137)).isoformat(),
            realized_pnl="-19.36",
        ),
        entry_price=Decimal(1),
        fills=[
            dict(
                at=AT,
                side="buy",
                effect="open",
                reason=None,
                price=Decimal(1),
                amount=Decimal("49.61"),
                fees=Decimal("0.87"),
            ),
            dict(
                at=AT + timedelta(seconds=137),
                side="sell",
                effect="close",
                reason="stop_loss",
                price=Decimal("0.61"),
                amount=Decimal("30.25"),
                fees=Decimal("0.5"),
            ),
        ],
        prices=prices,
    )


def test_trade_card_shows_pnl_peak_drawdown_hold_and_exit_reason():
    summary = trade_summary(_data())
    assert summary["best_percent"] == Decimal(50)
    assert summary["worst_percent"] == Decimal(-40)
    caption = chart_caption(_data())
    assert "🔴 SuperIntelligence Fund ($SIF) · closed" in caption
    assert "P&L: -19.36 USDT (-38.4%)" in caption
    assert "Entry → exit: -39.0% (fill price)" in caption
    assert "Best / worst while held: +50.0% / -40.0%" in caption
    assert "Held: 2m 17s" in caption and "Exit: stop-loss" in caption
    assert len(caption) <= 1024


def test_chart_png_marks_entry_and_exit():
    pytest.importorskip("matplotlib")
    png = render_chart_png(_data())
    assert png is not None and png.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_chart_query_binds_fills_and_nearby_trades_to_one_position():
    db = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await db.create_schema_for_tests()
    try:
        async with db.sessions() as session, session.begin():
            token = TokenRecord(id=uuid4(), mint=MINT, name="SIF", symbol="SIF")
            portfolio = PaperPortfolioRecord(
                id=uuid4(),
                name="Run",
                currency="USDT",
                initial_cash=Decimal(1000),
                cash_balance=Decimal(1000),
                active=True,
            )
            position = PaperPositionRecord(
                id=uuid4(),
                portfolio_id=portfolio.id,
                token_id=token.id,
                mint=MINT,
                strategy_key="aggressive",
                market_address=MINT,
                venue="pump_fun",
                lifecycle="bonding_curve",
                status="closed",
                token_quantity_raw=0,
                remaining_cost_basis=0,
                realized_pnl=Decimal("-19.36"),
                entry_price_raw=1,
                peak_price_raw=1,
                last_price_raw=1,
                opened_at=AT,
                closed_at=AT + timedelta(seconds=137),
            )
            session.add_all([token, portfolio, position])
            for offset, price in ((-600, "5"), (-30, "0.9"), (60, "1.5"), (900, "9")):
                event = uuid4()
                at = AT + timedelta(seconds=offset)
                session.add(
                    DomainEventRecord(
                        event_id=event,
                        event_type="token.trade",
                        schema_version=1,
                        provider="test",
                        source_event_at=at,
                        ingested_at=at,
                        payload={},
                    )
                )
                session.add(
                    TokenTradeRecord(
                        event_id=event,
                        token_id=token.id,
                        signature=str(event),
                        side="buy",
                        token_amount_raw=1,
                        quote_amount_raw=1,
                        price_raw=Decimal(price),
                        quote_asset="SOL",
                        source_event_at=at,
                    )
                )
            for side, effect, offset, price in (
                ("buy", "open", 0, "1"),
                ("sell", "close", 137, "0.61"),
            ):
                event = uuid4()
                at = AT + timedelta(seconds=offset)
                session.add(
                    DomainEventRecord(
                        event_id=event,
                        event_type="paper_order_completed",
                        schema_version=1,
                        provider="test",
                        source_event_at=at,
                        ingested_at=at,
                        payload={},
                    )
                )
                session.add(
                    PaperOrderRecord(
                        event_id=event,
                        portfolio_id=portfolio.id,
                        token_id=token.id,
                        mint=MINT,
                        trigger_event_id=event,
                        strategy_key="aggressive",
                        side=side,
                        status="filled",
                        position_effect=effect,
                        exit_reason="stop_loss" if side == "sell" else None,
                        venue="pump_fun",
                        lifecycle="bonding_curve",
                        requested_portfolio_amount=10,
                        filled_at=at,
                        created_at=at,
                        fill_json={
                            "actual_fill_price_raw": price,
                            "gross_portfolio_amount": "10",
                            "total_fee_portfolio": "1",
                        },
                    )
                )
        repo = PaperHistoryRepository(db.sessions)
        position_id = await repo.latest_closed_position_id(str(portfolio.id), MINT)
        assert position_id == str(position.id)
        data = await repo.chart(position_id)
        assert [float(price) for _, price in data["prices"]] == pytest.approx([0.9, 1.5])
        assert [(fill["side"], fill["price"]) for fill in data["fills"]] == [
            ("buy", Decimal(1)),
            ("sell", Decimal("0.61")),
        ]
        assert "Exit: stop-loss" in chart_caption(data)
    finally:
        await db.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("png", [b"\x89PNG", None])
async def test_close_notification_sends_trade_card(monkeypatch, png):
    photos, messages = [], []

    class FakeBot:
        def __init__(self, **kwargs):
            self.session = self

        async def close(self):
            pass

        async def send_message(self, user_id, message):
            messages.append(message)

        async def send_photo(self, user_id, photo, caption):
            photos.append(caption)

    async def card(portfolio_id, mint):
        return png, f"card {portfolio_id} {mint}"

    monkeypatch.setattr("memebot.telegram.notifications.Bot", FakeBot)
    notifier = TelegramTradeNotifier(
        "unused", frozenset({1}), minimum_interval_seconds=0, chart_lookup=card
    )
    await notifier.start()
    notifier._enqueue("plain fill text", MINT, "portfolio")
    await asyncio.wait_for(notifier._queue.join(), 2)
    await notifier.close()
    if png is None:
        assert messages[-1] == f"card portfolio {MINT}" and not photos
    else:
        assert photos == [f"card portfolio {MINT}"]


@pytest.mark.asyncio
async def test_markers_endpoint_validates_address_and_path():
    from memebot.telegram.markers_server import respond

    async def lookup(address):
        return {"mint": address, "fills": [], "open": None}

    assert (await respond(f"GET /fills?address={MINT} HTTP/1.1", lookup))[1]["mint"] == MINT
    assert (await respond("GET /fills?address=../etc HTTP/1.1", lookup))[0].startswith("400")
    assert (await respond(f"GET /other?address={MINT} HTTP/1.1", lookup))[0].startswith("404")
    assert (await respond(f"POST /fills?address={MINT} HTTP/1.1", lookup))[0].startswith("405")


@pytest.mark.asyncio
async def test_chart_markers_convert_fills_to_chart_units_by_mint_or_curve():
    db = Database(create_database_engine("sqlite+aiosqlite:///:memory:"))
    await db.create_schema_for_tests()
    curve = "CurveAddress1111111111111111111111111111111"
    try:
        async with db.sessions() as session, session.begin():
            token = TokenRecord(id=uuid4(), mint=MINT, name="SIF", symbol="SIF")
            portfolio = PaperPortfolioRecord(
                id=uuid4(),
                name="Run",
                currency="USDT",
                initial_cash=Decimal(1000),
                cash_balance=Decimal(1000),
                active=True,
            )
            position = PaperPositionRecord(
                id=uuid4(),
                portfolio_id=portfolio.id,
                token_id=token.id,
                mint=MINT,
                strategy_key="aggressive",
                market_address=curve,
                venue="pump_fun",
                lifecycle="bonding_curve",
                status="open",
                token_quantity_raw=1,
                remaining_cost_basis=Decimal(50),
                realized_pnl=Decimal(0),
                entry_price_raw=Decimal("0.0001"),  # not the fill unit; must not be used
                peak_price_raw=1,
                last_price_raw=1,
                opened_at=AT,
                execution_mark_json={"net_portfolio_value": "60"},
            )
            event = uuid4()
            session.add_all([token, portfolio, position])
            session.add(
                DomainEventRecord(
                    event_id=event,
                    event_type="paper_order_completed",
                    schema_version=1,
                    provider="test",
                    source_event_at=AT,
                    ingested_at=AT,
                    payload={},
                )
            )
            session.add(
                PaperOrderRecord(
                    event_id=event,
                    portfolio_id=portfolio.id,
                    token_id=token.id,
                    mint=MINT,
                    trigger_event_id=event,
                    strategy_key="aggressive",
                    side="buy",
                    status="filled",
                    position_effect="open",
                    venue="pump_fun",
                    lifecycle="bonding_curve",
                    requested_portfolio_amount=50,
                    filled_at=AT,
                    created_at=AT,
                    fill_json={
                        "actual_fill_price_raw": "0.00004",
                        "gross_portfolio_amount": "50",
                        "gross_quote_amount_raw": "500000000",
                        "quote_price_in_portfolio_currency": "100",
                    },
                )
            )
        repo = PaperHistoryRepository(db.sessions)
        by_mint, by_curve = await repo.chart_markers(MINT), await repo.chart_markers(curve)
        assert by_mint == by_curve
        fill = by_mint["fills"][0]
        assert fill["time"] == int(AT.timestamp()) and fill["sol"] == 0.5
        assert fill["mcap_sol"] == pytest.approx(40) and fill["mcap_usd"] == pytest.approx(4000)
        assert fill["price_usd"] == pytest.approx(4e-6)
        assert by_mint["open"]["mcap_usd"] == pytest.approx(4000)
        assert by_mint["open"]["pnl_percent"] == pytest.approx(20)
        assert await repo.chart_markers("Unknown111111111111111111111111111111") is None
    finally:
        await db.dispose()
