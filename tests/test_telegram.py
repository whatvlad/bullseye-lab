from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from memebot.events.models import StrategyDecisionCreated
from memebot.models.strategy import (
    ScoreResult,
    StrategyDecisionAction,
    StrategyRegime,
)
from memebot.telegram.access import is_allowed_user
from memebot.telegram.keyboards import (
    confirm_close_keyboard,
    dashboard_keyboard,
    positions_keyboard,
)
from memebot.telegram.notifications import (
    notification_for_event,
    tracked_wallet_notification,
)
from memebot.telegram.views import (
    daily_journal_view,
    dashboard_view,
    manual_result_view,
    parse_decimal,
    portfolio_view,
    positions_view,
    short_mint,
)


def test_daily_journal_formats_database_decimal_strings() -> None:
    text = daily_journal_view(
        {
            "date": "2026-08-23",
            "trades_opened": 3,
            "trades_closed": 2,
            "trades_still_open": 1,
            "wins": 1,
            "losses": 1,
            "win_rate_percent": "50.0",
            "realized_pnl": "-2.85636023",
            "average_mfe_percent": "12.346",
            "average_mae_percent": "-7.891",
            "exit_reasons": {},
            "top_rejections": {},
            "alpha_candidates": [],
        }
    )

    assert "Win rate: +50.00%" in text
    assert "Average MFE / MAE: +12.35% / -7.89%" in text
    assert "Realized P&L: -2.86" in text


def test_telegram_allowlist_is_default_deny() -> None:
    assert is_allowed_user(None, frozenset({123})) is False
    assert is_allowed_user(456, frozenset({123})) is False
    assert is_allowed_user(123, frozenset({123})) is True
    assert is_allowed_user(123, frozenset()) is False


def test_dashboard_exposes_required_button_groups() -> None:
    markup = dashboard_keyboard(paused=False)
    callbacks = {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }
    assert {
        "nav:portfolio",
        "nav:positions",
        "nav:wallets",
        "nav:signals",
        "nav:strategies",
        "control:pause",
        "nav:manual",
        "nav:watchlist",
        "nav:blacklist",
        "nav:settings",
    } <= callbacks
    labels = {button.text for row in markup.inline_keyboard for button in row}
    assert "⏹ Stop trading" in labels


def test_telegram_input_parsing_is_decimal_and_mint_safe() -> None:
    assert parse_decimal("12,5") == parse_decimal("12.5")
    assert short_mint("So11111111111111111111111111111111111111112") == "So1111…111112"


def test_tracked_wallet_notification_is_observation_only() -> None:
    text = tracked_wallet_notification(
        {
            "wallet": "11111111111111111111111111111111",
            "label": "Research wallet",
            "mint": "So11111111111111111111111111111111111111112",
            "symbol": "TEST",
            "side": "buy",
            "quote_amount_sol": "1.25",
            "signature": "a" * 64,
            "occurred_at": "2026-08-23T12:00:00+00:00",
            "realized_pnl_sol": "0.1",
            "unrealized_pnl_sol": "0.2",
        }
    )

    assert "Tracked wallet BUY" in text
    assert "1.2500 SOL" in text
    assert "did not copy this trade" in text


def test_portfolio_values_show_sol_usd_and_pnl_percent_with_human_precision() -> None:
    portfolio = {
        "name": "Paper",
        "currency": "USDT",
        "initial_cash": "1000.00000000",
        "cash_balance": "818.44433400",
        "open_cost_basis": "315.40378067",
        "realized_pnl": "133.84811467",
        "accounting_difference": "0.00000000",
        "accounting_reconciled": True,
        "positions": [],
        "display_rates": {
            "sol_in_portfolio_currency": "200",
            "sol_usd": "200",
        },
    }

    text = portfolio_view(portfolio)

    assert "Cash: 4.0922 SOL · $818.44" in text
    assert "Open cost basis: 1.5770 SOL · $315.40" in text
    assert "Realized P&L: +0.6692 SOL · +$133.85 (+13.38% of starting capital)" in text
    assert "818.44433400" not in text


def test_dashboard_falls_back_cleanly_when_sol_rate_is_unavailable() -> None:
    text = dashboard_view(
        {
            "portfolio": {
                "currency": "USDT",
                "cash_balance": "10.12345678",
                "open_cost_basis": "0",
                "realized_pnl": "1",
                "initial_cash": "10",
                "accounting_reconciled": True,
            }
        }
    )

    assert "Cash: 10.12 USDT (SOL rate unavailable)" in text
    assert "Realized P&L: +1.00 USDT (+10.00% of starting capital)" in text


def test_active_strategy_signal_notification_explains_the_decision() -> None:
    event = StrategyDecisionCreated(
        event_id=UUID(int=1),
        provider="test",
        source_event_at=datetime(2026, 8, 23, tzinfo=UTC),
        mint="So11111111111111111111111111111111111111112",
        strategy_key="balanced",
        strategy_version_id=UUID(int=2),
        active_strategy=True,
        action=StrategyDecisionAction.ENTER_CANDIDATE,
        regime=StrategyRegime.EARLY_MOMENTUM,
        risk_event_id=UUID(int=3),
        score=ScoreResult(
            final_score=Decimal("72.5"),
            component_completeness_percent=Decimal(80),
            components=(),
        ),
        reasons=("score_at_or_above_entry_threshold:65",),
    )

    notification = notification_for_event(event)

    assert notification is not None
    assert "paper buy candidate" in notification[1]
    assert "Score: 72.50/100" in notification[1]
    assert "score at or above entry threshold: 65" in notification[1]


def test_open_positions_have_direct_close_buttons() -> None:
    mint = "So11111111111111111111111111111111111111112"
    markup = positions_keyboard([{"mint": mint}])
    callbacks = [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert f"position:confirm:{mint}" in callbacks
    assert "positions:close_all:confirm" in callbacks


def test_position_close_has_fresh_and_force_paths() -> None:
    mint = "So11111111111111111111111111111111111111112"
    markup = confirm_close_keyboard(mint)
    callbacks = {button.callback_data for row in markup.inline_keyboard for button in row}
    assert f"position:close:{mint}" in callbacks
    assert f"position:force:{mint}" in callbacks


def test_pending_manual_close_view_explains_fresh_wait_and_force_option() -> None:
    text = manual_result_view(
        {
            "kind": "pending_paper_action",
            "mint": "So11111111111111111111111111111111111111112",
            "expires_at": "2026-08-23T00:00:30+00:00",
        }
    )
    assert "waiting for the next fresh market trade" in text
    assert "force a degraded close" in text


def test_position_card_identifies_memecoin_and_shows_estimated_pnl() -> None:
    portfolio = {
        "currency": "USDT",
        "display_rates": {
            "sol_in_portfolio_currency": "200",
            "sol_usd": "200",
        },
        "positions": [
            {
                "mint": "So11111111111111111111111111111111111111112",
                "name": "Moon Dog",
                "symbol": "MDOG",
                "strategy_key": "balanced",
                "venue": "pump_fun",
                "lifecycle": "bonding_curve",
                "remaining_cost_basis": "100",
                "entry_price_raw": "2",
                "last_price_raw": "3",
                "execution_mark_json": {"net_portfolio_value": "150"},
                "execution_mark_valid": True,
                "opened_at": "2026-08-23T12:00:00+00:00",
            }
        ],
    }

    text = positions_view(portfolio)

    assert "Moon Dog ($MDOG)" in text
    assert "Estimated value: 0.7500 SOL · $150.00" in text
    assert "Unrealized P&L: +0.2500 SOL · +$50.00 (+50.00%)" in text
    portfolio["positions"][0]["execution_mark_valid"] = False
    stale_text = positions_view(portfolio)
    assert "Unrealized P&L: unknown" in stale_text
    assert "Execution mark unavailable or stale" in stale_text
    assert "+$50.00" not in stale_text
