from __future__ import annotations

from decimal import Decimal
from typing import Any

from memebot.storage.database.control import TradingControlSnapshot


def dashboard_view(payload: dict[str, Any]) -> str:
    portfolio = payload.get("portfolio") or {}
    control = payload.get("control")
    providers = payload.get("provider_health") or []
    provider_state = ", ".join(_provider_state(item) for item in providers) or "no health data"
    if isinstance(control, TradingControlSnapshot):
        mode = "MONITORING — NEW BUYS STOPPED" if control.entries_paused else "TRADING ACTIVE"
        strategy = control.active_strategy_key.title()
    else:
        mode = "UNINITIALIZED"
        strategy = "unknown"
    return (
        "🎯 Bullseye Paper Trading\n\n"
        f"Status: {mode}\n"
        f"Active strategy: {strategy}\n"
        f"{_amount_line('Cash', portfolio.get('cash_balance'), portfolio)}\n"
        f"{_amount_line('Open cost basis', portfolio.get('open_cost_basis'), portfolio)}\n"
        f"{_pnl_line(portfolio)}\n"
        f"Accounting reconciled: {portfolio.get('accounting_reconciled', False)}\n"
        f"Providers: {provider_state}\n\n"
        "Paper mode only — no real transactions or signing."
    )


def portfolio_view(portfolio: dict[str, Any] | None) -> str:
    if portfolio is None:
        return "No active paper portfolio."
    positions = portfolio.get("positions") or []
    return (
        f"💼 {portfolio['name']}\n\n"
        f"{_amount_line('Starting capital', portfolio['initial_cash'], portfolio)}\n"
        f"{_amount_line('Cash', portfolio['cash_balance'], portfolio)}\n"
        f"{_amount_line('Open cost basis', portfolio['open_cost_basis'], portfolio)}\n"
        f"{_pnl_line(portfolio)}\n"
        f"Open positions: {len(positions)}\n"
        f"Accounting difference: {_plain_number(portfolio['accounting_difference'])}"
    )


def positions_view(portfolio: dict[str, Any] | None) -> str:
    if portfolio is None:
        return "📊 No open paper positions."
    positions = portfolio.get("positions") or []
    if not positions:
        return "📊 No open paper positions."
    lines = ["📊 Open paper positions", ""]
    for item in positions[:15]:
        symbol = _display_symbol(item.get("symbol"))
        name = item.get("name") or "Unnamed token"
        estimated_value, unrealized_pnl, unrealized_percent = _position_valuation(item)
        lines.extend(
            (
                f"🪙 {name} ({symbol})",
                f"Mint: {item['mint']}",
                f"https://solscan.io/token/{item['mint']}",
                f"Strategy: {item['strategy_key'].title()}",
                f"Venue: {item['venue']} · Stage: {item['lifecycle']}",
                _amount_line("Cost basis", item["remaining_cost_basis"], portfolio),
                _amount_line("Estimated value", estimated_value, portfolio)
                if estimated_value is not None
                else "Execution mark unavailable or stale",
                (
                    f"Unrealized P&L: {_signed_amount(unrealized_pnl, portfolio)} "
                    f"({_short_percent(unrealized_percent)})"
                    if unrealized_pnl is not None
                    else "Unrealized P&L: unknown"
                ),
                f"Opened: {str(item['opened_at'])[:19].replace('T', ' ')} UTC",
                "",
            )
        )
    return "\n".join(lines)


def position_close_confirmation(position: dict[str, Any], portfolio: dict[str, Any]) -> str:
    symbol = _display_symbol(position.get("symbol"))
    name = position.get("name") or "Unnamed token"
    return (
        "⚠️ Close paper position?\n\n"
        f"Token: {name} ({symbol})\n"
        f"Mint: {position['mint']}\n"
        f"{_amount_line('Remaining cost basis', position['remaining_cost_basis'], portfolio)}\n\n"
        "Close refreshes canonical execution state over RPC, including migration recovery.\n"
        "A fresh executable quote is required; old reserves cannot authorize a fill.\n\n"
        "Both options simulate selling the entire remaining position. "
        "No real Solana transaction will be sent."
    )


def close_all_confirmation(portfolio: dict[str, Any]) -> str:
    positions = portfolio.get("positions") or []
    total_cost = sum(
        (Decimal(str(item["remaining_cost_basis"])) for item in positions),
        start=Decimal(0),
    )
    return (
        "🛑 Close every paper position?\n\n"
        f"Positions: {len(positions)}\n"
        f"Combined cost basis: {total_cost:,.2f} {portfolio['currency']}\n\n"
        "New entries will be paused first. Positions without a fresh executable quote "
        "remain pending recovery. Old reserves cannot authorize a fill.\n\n"
        "No real Solana transaction will be sent."
    )


def close_all_result_view(result: dict[str, Any]) -> str:
    return (
        "🛑 Close-all paper request processed\n\n"
        f"Positions found: {result['total']}\n"
        f"Closed immediately: {result['filled']}\n"
        f"Waiting for fresh trade: {result['pending']}\n"
        f"Failed/already closed: {result['failed']}\n\n"
        "New entries remain paused. No real transactions were created."
    )


def strategies_view(strategies: list[dict[str, Any]], control: TradingControlSnapshot) -> str:
    lines = ["🧠 Strategy selection", ""]
    for item in strategies:
        marker = "✅" if item["strategy_key"] == control.active_strategy_key else "▫️"
        config = item["configuration"]
        lines.append(
            f"{marker} {item['display_name']} — entry {config['score_threshold']}, "
            f"max risk {config['maximum_risk_score']}"
        )
    return "\n".join(lines)


def comparison_view(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No strategy decisions recorded yet."
    lines = ["📈 Strategy comparison", ""]
    for row in rows:
        lines.append(
            f"• {row['strategy'].title()}: decisions {row['decisions']}, "
            f"candidates {row['entry_candidates']}, fills {row['fills']}"
        )
    return "\n".join(lines)


def settings_view(control: TradingControlSnapshot) -> str:
    return (
        "⚙️ Runtime paper settings\n\n"
        f"Fixed entry position: {control.base_position_percent}%\n"
        f"Score scaling: OFF (configured ceiling {control.max_position_percent}%)\n"
        f"Max open positions: {control.max_open_positions}\n"
        f"Stop loss: {control.stop_loss_percent}%\n"
        f"Take profit: {control.take_profit_percent}%\n"
        f"Trailing stop: {control.trailing_stop_percent}%\n"
        f"Max holding: {control.max_holding_seconds}s\n"
        f"SOL tiers (score <70 / 70-85 / 85+): {_sol_tiers_text(control)}"
    )


def _sol_tiers_text(control: TradingControlSnapshot) -> str:
    if control.sol_tier_small is None:
        return "defaults from .env (top tier = whole portfolio)"
    return " / ".join(
        f"{value.normalize():f} SOL"
        for value in (control.sol_tier_small, control.sol_tier_medium, control.sol_tier_large)
        if value is not None
    )


def signals_view(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "📡 No watch/entry signals recorded yet."
    lines = ["📡 Latest signals", ""]
    for row in rows:
        label = row["symbol"] or short_mint(row["mint"])
        lines.append(
            f"• {label} | {row['strategy']} | {row['action']} | "
            f"score {row['score']} | {row['regime']}"
        )
    return "\n".join(lines)


def outcomes_view(summary: dict[str, Any]) -> str:
    closed = int(summary["closed_trade_count"])
    winners = int(summary["winning_trade_count"])
    win_rate = Decimal(winners) / Decimal(closed) * Decimal(100) if closed else None
    return (
        "📈 Phase 7 outcomes\n\n"
        f"Decisions tracked: {summary['decision_count']}\n"
        f"Skipped/watch tracked: {summary['skipped_or_watch_count']}\n"
        "Skipped with positive excursion: "
        f"{summary['skipped_with_positive_excursion']}\n"
        f"Paper trades tracked: {summary['taken_trade_count']}\n"
        f"Open / closed: {summary['open_trade_count']} / {closed}\n"
        f"Winning / losing: {winners} / {summary['losing_trade_count']}\n"
        f"Win rate: {_short_percent(win_rate)}\n"
        f"Recorded realized P&L: {_plain_number(summary['realized_pnl'], signed=True)}\n\n"
        "MFE/MAE and future returns are recorded from event-time market data."
    )


def daily_journal_view(report: dict[str, Any]) -> str:
    exits = report.get("exit_reasons") or {}
    rejections = report.get("top_rejections") or {}
    candidates = report.get("alpha_candidates") or []
    lines = [
        f"📓 Trading journal · {report['date']}",
        "",
        f"Opened / closed / still open: {report['trades_opened']} / "
        f"{report['trades_closed']} / {report['trades_still_open']}",
        f"Wins / losses: {report['wins']} / {report['losses']}",
        f"Win rate: {_short_percent(report.get('win_rate_percent'))}",
        f"Realized P&L: {_plain_number(report['realized_pnl'], signed=True)}",
        f"Average MFE / MAE: {_short_percent(report.get('average_mfe_percent'))} / "
        f"{_short_percent(report.get('average_mae_percent'))}",
    ]
    if exits:
        lines.extend(("", "Exit reasons:"))
        lines.extend(f"• {key.replace('_', ' ')}: {value}" for key, value in exits.items())
    if rejections:
        lines.extend(("", "Most common rejected entries:"))
        lines.extend(f"• {key.replace('_', ' ')}: {value}" for key, value in rejections.items())
    if candidates:
        lines.extend(("", "Latest Alpha Filter candidates:"))
        for item in candidates:
            label = item.get("symbol") or short_mint(str(item["mint"]))
            holder = item.get("holder_profile") or {}
            tags = ", ".join(
                f"{tag} {holder[tag]}%"
                for tag in ("dev", "insider", "bundler", "sniper")
                if holder.get(tag) is not None
            )
            lines.append(
                f"• {label}: {item.get('market_regime', 'unknown')}"
                + (f" · {tags}" if tags else "")
            )
    lines.extend(("", "Alpha Filter market/deployer reasons are shadow research signals."))
    return "\n".join(lines)


def wallets_view(wallets: list[dict[str, Any]]) -> str:
    if not wallets:
        return (
            "🧭 Wallet intelligence\n\nNo wallets observed yet. "
            "Keep the market worker running or add a tracked wallet."
        )
    lines = [
        "🧭 Wallet intelligence",
        "",
        "⭐ means actively tracked with trade alerts.",
        "Analytics are research-only and never auto-copy trades.",
        "",
    ]
    for wallet in wallets[:15]:
        marker = "⭐" if wallet["seeded"] else "▫️"
        label = wallet.get("label") or short_mint(wallet["address"])
        metrics = wallet.get("metrics") or {}
        lines.append(
            f"{marker} {label} · alpha {wallet.get('alpha_score') or 'n/a'} · "
            f"{wallet['confidence']} · samples {metrics.get('sample_size', 0)}"
        )
    return "\n".join(lines)


def wallet_detail_view(wallet: dict[str, Any] | None) -> str:
    if wallet is None:
        return "Wallet not found in local observations."
    metrics = wallet.get("metrics") or {}
    portfolio = wallet.get("portfolio") or {}
    lines = [
        "🔎 Tracked wallet analytics",
        "",
        f"Label: {wallet.get('label') or 'none'}\nAddress: {wallet['address']}",
        f"Tracking alerts: {'ON' if wallet.get('tracked') else 'OFF'}",
        f"Status / confidence: {wallet['status']} / {wallet['confidence']}",
        f"Alpha score: {wallet.get('alpha_score') or 'n/a'}/100",
        f"Observed Pump trades: {wallet['observed_trade_count']}",
        "",
        "Observed portfolio:",
        f"• Open tokens: {portfolio.get('open_token_count', 0)}",
        f"• Realized P&L: {_plain_number(portfolio.get('realized_pnl_sol', 0), signed=True)} SOL",
        "• Unrealized P&L: "
        f"{_plain_number(portfolio.get('unrealized_pnl_sol', 0), signed=True)} SOL",
        f"• Total P&L: {_plain_number(portfolio.get('total_pnl_sol', 0), signed=True)} SOL",
        "",
        "Behavior:",
        f"• Launch samples: {metrics.get('sample_size', 0)}",
        f"• Closed samples: {metrics.get('closed_samples', 0)}",
        f"• Positive win rate: {metrics.get('win_rate_positive_percent', '0')}%",
        f"• Median return: {metrics.get('median_return_percent') or 'n/a'}%",
        f"• Early-entry frequency: {metrics.get('early_entry_frequency_percent', '0')}%",
        f"• Early-success frequency: {metrics.get('early_success_frequency_percent', '0')}%",
        f"• Rug exposure: {metrics.get('rug_exposure_percent', '0')}%",
    ]
    outcomes = wallet.get("recent_token_outcomes") or []
    if outcomes:
        lines.extend(("", "Recent token outcomes:"))
        for item in outcomes[:6]:
            token = item.get("symbol") or item.get("name") or short_mint(item["mint"])
            state = "closed" if item.get("closed") else "open"
            lines.append(
                f"• {token} · {state} · realised "
                f"{_plain_number(item.get('realized_pnl_sol', 0), signed=True)} SOL · "
                f"unrealised {_plain_number(item.get('unrealized_pnl_sol', 0), signed=True)} SOL"
            )
    activity = wallet.get("recent_activity") or []
    if activity:
        lines.extend(("", "Latest observed actions:"))
        for item in activity[:8]:
            token = item.get("symbol") or item.get("name") or short_mint(item["mint"])
            lines.append(
                f"• {str(item['side']).upper()} {token} · "
                f"{_plain_number(item['quote_amount_sol'])} SOL · "
                f"{str(item['occurred_at'])[11:19]} UTC"
            )
    lines.extend(("", "Observation only — Bullseye never copy-trades this wallet."))
    return "\n".join(lines)


def token_controls_view(kind: str, rows: list[dict[str, Any]]) -> str:
    title = "👁 Watchlist" if kind == "watchlist" else "⛔ Blacklist"
    if not rows:
        return f"{title}\n\nNo tokens."
    return title + "\n\n" + "\n".join(f"• {short_mint(row['mint'])}" for row in rows[:30])


def manual_result_view(payload: dict[str, Any]) -> str:
    if payload.get("kind") == "pending_paper_action":
        return (
            "⏳ Manual paper close queued\n"
            f"Mint: {short_mint(payload['mint'])}\n"
            "Status: waiting for the next fresh market trade\n"
            f"Timeout: {payload['expires_at']}\n\n"
            "Bullseye will close automatically on fresh reserves. You can also "
            "force a degraded close using the last known snapshot.\n\n"
            "No real transaction was created."
        )
    result = payload["result"]
    status = str(result["status"]).upper()
    detail = result.get("rejection_reason") or result.get("exit_reason") or "simulated fill"
    degraded = ""
    fill = result.get("fill")
    if fill and fill.get("fill_quality") == "degraded":
        evidence = fill.get("evidence") or []
        age = next(
            (
                item.get("value")
                for item in evidence
                if item.get("code") == "forced_stale_market_age_seconds"
            ),
            "unknown",
        )
        degraded = (
            f"\nFill quality: DEGRADED\nSnapshot age: {age} seconds"
            "\nWarning: P&L uses the last known reserves."
        )
    return (
        f"🧾 Manual paper order: {status}\n"
        f"Side: {result['side']}\n"
        f"Mint: {short_mint(payload['mint'])}\n"
        f"Result: {detail}{degraded}\n\n"
        "No real transaction was created."
    )


def parse_decimal(text: str) -> Decimal:
    try:
        return Decimal(text.strip().replace(",", "."))
    except Exception as error:
        raise ValueError("invalid_decimal") from error


def short_mint(mint: str) -> str:
    return f"{mint[:6]}…{mint[-6:]}"


def _provider_state(item: dict[str, Any]) -> str:
    if item.get("error_code") == "pumpportal_daily_trade_budget_reached":
        return f"{item['provider']}: discovery active, daily trade budget reached"
    return f"{item['provider']}: {item['state']}"


def _amount_line(label: str, raw_amount: Any, portfolio: dict[str, Any]) -> str:
    amount = _decimal_or_none(raw_amount)
    rates = portfolio.get("display_rates") or {}
    sol_rate = _decimal_or_none(rates.get("sol_in_portfolio_currency"))
    sol_usd = _decimal_or_none(rates.get("sol_usd"))
    if amount is not None and sol_rate is not None and sol_usd is not None and sol_rate > 0:
        sol = amount / sol_rate
        usd = sol * sol_usd
        return f"{label}: {_format_sol(sol)} · {_format_usd(usd)}"
    if amount is not None:
        currency = portfolio.get("currency", "")
        return f"{label}: {_plain_number(amount)} {currency} (SOL rate unavailable)"
    return f"{label}: n/a"


def _pnl_line(portfolio: dict[str, Any]) -> str:
    pnl = _decimal_or_none(portfolio.get("realized_pnl"))
    initial = _decimal_or_none(portfolio.get("initial_cash"))
    rates = portfolio.get("display_rates") or {}
    sol_rate = _decimal_or_none(rates.get("sol_in_portfolio_currency"))
    sol_usd = _decimal_or_none(rates.get("sol_usd"))
    percent = pnl / initial * Decimal(100) if pnl is not None and initial else None
    if pnl is not None and sol_rate is not None and sol_usd is not None and sol_rate > 0:
        sol = pnl / sol_rate
        usd = sol * sol_usd
        return (
            f"Realized P&L: {_format_sol(sol, signed=True)} · "
            f"{_format_usd(usd, signed=True)} ({_format_percent(percent)})"
        )
    if pnl is not None:
        currency = portfolio.get("currency", "")
        return (
            f"Realized P&L: {_plain_number(pnl, signed=True)} {currency} "
            f"({_format_percent(percent)})"
        )
    return "Realized P&L: n/a"


def _decimal_or_none(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except Exception:
        return None


def _format_sol(value: Decimal, *, signed: bool = False) -> str:
    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}{value:,.4f} SOL"


def _format_usd(value: Decimal, *, signed: bool = False) -> str:
    if value < 0:
        return f"-${abs(value):,.2f}"
    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}${value:,.2f}"


def _format_percent(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    prefix = "+" if value > 0 else ""
    return f"{prefix}{value:.2f}% of starting capital"


def _plain_number(value: Any, *, signed: bool = False) -> str:
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number:,.2f}"


def _position_valuation(
    item: dict[str, Any],
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    cost = Decimal(str(item["remaining_cost_basis"]))
    mark = item.get("execution_mark_json")
    if not item.get("execution_mark_valid") or not isinstance(mark, dict):
        return None, None, None
    estimated = Decimal(str(mark["net_portfolio_value"]))
    pnl = estimated - cost
    percent = pnl / cost * Decimal(100) if cost > 0 else None
    return estimated, pnl, percent


def _signed_amount(amount: Decimal, portfolio: dict[str, Any]) -> str:
    rates = portfolio.get("display_rates") or {}
    sol_rate = _decimal_or_none(rates.get("sol_in_portfolio_currency"))
    sol_usd = _decimal_or_none(rates.get("sol_usd"))
    if sol_rate is not None and sol_usd is not None and sol_rate > 0:
        return (
            f"{_format_sol(amount / sol_rate, signed=True)} · "
            f"{_format_usd(amount / sol_rate * sol_usd, signed=True)}"
        )
    return f"{_plain_number(amount, signed=True)} {portfolio.get('currency', '')}"


def _short_percent(value: Any) -> str:
    number = _decimal_or_none(value)
    if number is None:
        return "n/a"
    prefix = "+" if number > 0 else ""
    return f"{prefix}{number:.2f}%"


def _display_symbol(value: Any) -> str:
    if not value:
        return "symbol unavailable"
    symbol = str(value)
    return symbol if symbol.startswith("$") else f"${symbol}"
