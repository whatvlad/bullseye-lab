# ruff: noqa: RUF001
from __future__ import annotations

from collections import Counter
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .filters import TABS

TITLES = {"newPairs": "New Pairs", "finalStretch": "Final Stretch", "migrated": "Migrated"}


def pulse_keyboard(tab: str = "all", page: int = 0) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=title, callback_data=f"pulse:{key}:0")
            for key, title in TITLES.items()
        ]
    ]
    if tab != "all":
        buttons.append(
            [
                InlineKeyboardButton(text="←", callback_data=f"pulse:{tab}:{max(0, page - 1)}"),
                InlineKeyboardButton(text="Обновить", callback_data=f"pulse:{tab}:{page}"),
                InlineKeyboardButton(text="→", callback_data=f"pulse:{tab}:{page + 1}"),
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(text="Все стадии", callback_data="pulse:all:0"),
            InlineKeyboardButton(text="Dashboard", callback_data="nav:dashboard"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def money(value: Any) -> str:
    return "нет данных" if value is None else f"${float(value):,.0f}"


def pulse_view(payload: dict[str, Any] | None, tab: str = "all", page: int = 0) -> str:
    if payload is None:
        return "Pulse выключен в настройках."
    lines = [
        "PULSE · PAPER",
        f"Обновлено: {payload['observed_at'][:19]} UTC",
        "Фильтры: config/pulse.json · наблюдаемая выборка, не весь рынок",
    ]
    tabs = TABS if tab == "all" else (tab,)
    for key in tabs:
        rows = payload["groups"][key]
        excluded = payload["rejected"][key]
        size = 2 if tab == "all" else 5
        page_number = min(max(0, page), max(0, (len(rows) - 1) // size))
        visible = rows[page_number * size : (page_number + 1) * size]
        lines.append(f"\n{TITLES[key]} · {len(rows)} прошли / {len(excluded)} отсеяны")
        for row in visible:
            risk = (
                "risk ✓"
                if row["risk_allowed"] is True
                else "risk ✕"
                if row["risk_allowed"] is False
                else "risk ?"
            )
            symbol = str(row.get("symbol") or "Без тикера").replace("\n", " ")[:24]
            lines.extend(
                [
                    f"{symbol} · {risk} · MC {money(row['marketCap'])}",
                    f"SOL-ликв. {money(row['liquidity'])} · V5m {money(row['volume'])}",
                    row["mint"],
                ]
            )
        if not visible:
            lines.append("Нет кандидатов с подтверждёнными данными по этому фильтру.")
        reasons = Counter(reason for row in excluded for reason in row["filter_reasons"])
        if reasons:
            lines.append(
                "Отсев: "
                + "; ".join(f"{reason} ×{count}" for reason, count in reasons.most_common(3))
            )
    lines.append(
        f"\nПросмотрено {payload['scanned']} последних монет за 24ч"
        + ("; лимит 300 достигнут" if payload["truncated"] else "")
    )
    lines.append(
        "Источники: Pump/PumpSwap, SOL. Остальные протоколы из экспорта пока не подключены."
    )
    lines.append(
        "Прошёл Pulse ≠ сигнал покупки. Далее проверяются стратегия, risk, размер и комиссии."
    )
    return "\n".join(lines)[:3900]
