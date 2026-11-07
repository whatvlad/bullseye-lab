"""Entry/exit chart and summary for one PAPER position, sent as a Telegram photo."""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from typing import Any

_REASONS = {
    "stop_loss": "stop-loss",
    "take_profit": "take-profit",
    "partial_take_profit": "partial take-profit",
    "trailing_stop": "trailing stop",
    "maximum_holding_time": "max hold time",
    "dump_hazard": "dump hazard",
    "stagnation": "stagnation",
}


def trade_summary(data: dict[str, Any]) -> dict[str, Any]:
    position = data["position"]
    fills = data["fills"]
    buys = [item for item in fills if item["side"] == "buy"]
    sells = [item for item in fills if item["side"] == "sell"]
    entry = buys[0]["price"] if buys else Decimal(str(data["entry_price"]))
    invested = sum((item["amount"] + item["fees"] for item in buys), start=Decimal(0))
    pnl = Decimal(position["realized_pnl"])
    opened = datetime.fromisoformat(position["opened_at"])
    closed = datetime.fromisoformat(position["closed_at"]) if position["closed_at"] else None
    held = [
        price for at, price in data["prices"] if at >= opened and (closed is None or at <= closed)
    ]
    return dict(
        entry=entry,
        exit=sells[-1]["price"] if sells else None,
        invested=invested,
        pnl=pnl,
        pnl_percent=pnl / invested * 100 if invested > 0 else None,
        best_percent=(max(held) / entry - 1) * 100 if held and entry > 0 else None,
        worst_percent=(min(held) / entry - 1) * 100 if held and entry > 0 else None,
        held_seconds=((closed or opened) - opened).total_seconds() if closed else None,
        exit_reason=_REASONS.get(sells[-1]["reason"] or "", sells[-1]["reason"]) if sells else None,
        sells=len(sells),
        sol_price=next(
            (item.get("sol_price") for item in reversed(fills) if item.get("sol_price")), None
        ),
    )


def chart_caption(data: dict[str, Any]) -> str:
    position = data["position"]
    summary = trade_summary(data)
    currency = position["currency"]
    name = position.get("name") or "Unnamed token"
    symbol = f" (${position['symbol']})" if position.get("symbol") else ""
    closed = position["status"] == "closed"
    pnl, percent = summary["pnl"], summary["pnl_percent"]
    icon = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
    lines = [
        f"{icon} {name}{symbol} · {'closed' if closed else 'open'}",
        "P&L: " + pnl_text(pnl, currency, summary["sol_price"], percent),
        f"Invested: {summary['invested']:,.2f} {currency}",
        f"Entry → exit: {_change(summary['entry'], summary['exit'])}",
    ]
    if summary["best_percent"] is not None:
        lines.append(
            f"Best / worst while held: {summary['best_percent']:+.1f}% / "
            f"{summary['worst_percent']:+.1f}%"
        )
    if summary["held_seconds"] is not None:
        lines.append(f"Held: {_duration(summary['held_seconds'])}")
    if summary["exit_reason"]:
        lines.append(f"Exit: {summary['exit_reason']}")
    lines.append(f"https://dexscreener.com/solana/{position['mint']}")
    return "\n".join(lines)


def render_chart_png(data: dict[str, Any]) -> bytes | None:
    """Price as % from entry, with BUY/SELL markers. None if matplotlib is missing."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    summary = trade_summary(data)
    entry = summary["entry"]
    if not data["prices"] or entry <= 0:
        return None
    position = data["position"]
    times = [at for at, _ in data["prices"]]
    values = [float((price / entry - 1) * 100) for _, price in data["prices"]]
    opened = datetime.fromisoformat(position["opened_at"])
    closed = datetime.fromisoformat(position["closed_at"]) if position["closed_at"] else times[-1]

    figure, axis = plt.subplots(figsize=(8, 4.2), dpi=120)
    figure.patch.set_facecolor("#111418")
    axis.set_facecolor("#111418")
    axis.axvspan(opened, closed, color="#2a3340", alpha=0.6, lw=0)
    axis.axhline(0, color="#8a94a6", lw=0.8, ls="--")
    axis.plot(times, values, color="#e8edf4", lw=1.3, drawstyle="steps-post")
    for item in data["fills"]:
        y = float((item["price"] / entry - 1) * 100)
        buy = item["side"] == "buy"
        axis.scatter(
            [item["at"]],
            [y],
            marker="^" if buy else "v",
            s=110,
            color="#2fbf71" if buy else "#ef4b4b",
            edgecolors="white",
            linewidths=0.8,
            zorder=5,
        )
        label = "BUY" if buy else _REASONS.get(item["reason"] or "", "SELL").upper()
        axis.annotate(
            f"{label} {y:+.1f}%",
            (item["at"], y),
            textcoords="offset points",
            xytext=(6, 10 if buy else -16),
            color="#e8edf4",
            fontsize=8,
        )
    name = position.get("symbol") or position.get("name") or position["mint"][:8]
    pnl, percent = summary["pnl"], summary["pnl_percent"]
    axis.set_title(
        f"{name} · P&L {pnl:+,.2f} {position['currency']}"
        + (f" ({percent:+.1f}%)" if percent is not None else ""),
        color="#2fbf71" if pnl > 0 else "#ef4b4b" if pnl < 0 else "#e8edf4",
        fontsize=11,
    )
    axis.set_ylabel("% from entry", color="#8a94a6")
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    axis.tick_params(colors="#8a94a6", labelsize=8)
    for spine in axis.spines.values():
        spine.set_color("#2a3340")
    axis.grid(color="#20262e", lw=0.6)
    figure.autofmt_xdate()
    figure.tight_layout()
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", facecolor=figure.get_facecolor())
    plt.close(figure)
    return buffer.getvalue()


def pnl_text(
    pnl: Decimal, currency: str, sol_price: Decimal | None, percent: Decimal | None
) -> str:
    """'+0.0508 SOL · +5.40 USDT · +49.5%' (SOL omitted without a SOL price)."""
    parts = [f"{pnl / sol_price:+.4f} SOL"] if sol_price else []
    parts.append(f"{pnl:+,.2f} {currency}")
    if percent is not None:
        parts.append(f"{percent:+.1f}%")
    return " · ".join(parts)


def _change(entry: Decimal, exit_price: Decimal | None) -> str:
    if exit_price is None or entry <= 0:
        return "still open"
    return f"{(exit_price / entry - 1) * 100:+.1f}% (fill price)"


def _duration(seconds: float) -> str:
    minutes, rest = divmod(int(seconds), 60)
    return f"{minutes}m {rest:02d}s" if minutes else f"{rest}s"


async def trade_card(history: Any, position_id: str) -> tuple[bytes | None, str] | None:
    """Chart image (None without matplotlib) and caption for one position."""
    data = await history.chart(position_id)
    if data is None:
        return None
    return render_chart_png(data), chart_caption(data)


async def closed_trade_card(
    history: Any, portfolio_id: str, mint: str
) -> tuple[bytes | None, str] | None:
    position_id = await history.latest_closed_position_id(portfolio_id, mint)
    return None if position_id is None else await trade_card(history, position_id)
