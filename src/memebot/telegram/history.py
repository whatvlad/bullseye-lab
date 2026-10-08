from __future__ import annotations

from decimal import Decimal
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def coin_identity(mint: str, info: dict[str, Any] | None = None) -> str:
    info = info or {}
    name = " ".join(str(info.get("name") or "Название неизвестно").split())[:80]
    symbol = " ".join(str(info.get("symbol") or "").split())[:24]
    return (f"{name} ({symbol})" if symbol else name) + f"\nMint: {mint}"


def coin_links(mint: str) -> str:
    return f"https://solscan.io/token/{mint}\nhttps://dexscreener.com/solana/{mint}"


def position_card(item: dict[str, Any]) -> str:
    status = "ЗАКРЫТА" if item["status"] == "closed" else "ОТКРЫТА — итог ещё не определён"
    currency = item["currency"]
    lines = [
        coin_identity(item["mint"], item),
        f"Статус: {status}",
        f"Вход: {item['opened_at'][:19].replace('T', ' ')} UTC",
    ]
    if item["closed_at"]:
        lines.append(f"Закрытие: {item['closed_at'][:19].replace('T', ' ')} UTC")
    lines.append(f"Зафиксированный PnL: {Decimal(item['realized_pnl']):+,.2f} {currency}")
    if item["status"] != "closed":
        lines.append(
            f"Себестоимость остатка: {Decimal(item['remaining_cost_basis']):,.2f} {currency}"
        )
    if item["partial_take_profit_taken"]:
        lines.append("Была частичная фиксация прибыли")
    return "\n".join(lines)


def history_view(payload: dict[str, Any]) -> str:
    lines = [
        f"📚 История PAPER — все портфели · {payload['total']} позиций",
        f"Страница {payload['page'] + 1}/{payload['pages']}",
        "Зафиксированный PnL по валютам: "
        + (
            ", ".join(
                f"{Decimal(value):+,.2f} {currency}"
                for currency, value in payload["realized_by_currency"].items()
            )
            or "нет сделок"
        ),
        "Открой монету ниже для всех её покупок и продаж. "
        "Полная выгрузка включает отклонённые заявки.",
        "",
    ]
    lines.extend(position_card(item) + "\n" for item in payload["items"])
    return "\n".join(lines)


def detail_view(payload: dict[str, Any]) -> str:
    item = payload["position"]
    lines = [
        position_card(item),
        f"Портфель: {str(item['portfolio'])[:100]}",
        coin_links(item["mint"]),
        "",
        f"Исполненные PAPER-заявки: {payload['total']} · "
        f"страница {payload['page'] + 1}/{payload['pages']}",
    ]
    for order in payload["orders"]:
        action = (
            "ПОКУПКА"
            if order["side"] == "buy"
            else ("ЧАСТИЧНАЯ ПРОДАЖА" if order["effect"] == "partial_close" else "ПРОДАЖА")
        )
        lines.extend(
            [
                "",
                f"{action} · {order['at'][:19].replace('T', ' ')} UTC",
                f"Объём: {Decimal(order['amount'] or '0'):,.2f} {item['currency']}",
                f"Комиссии: {Decimal(order['fees'] or '0'):,.2f} {item['currency']}",
                f"Причина: {str(order['reason'] or 'strategy entry')[:120]}",
            ]
        )
    return "\n".join(lines)


def history_keyboard(payload: dict[str, Any]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=str(item.get("symbol") or item.get("name") or item["mint"])[:40],
                callback_data=f"history:coin:{item['id']}:0",
            )
        ]
        for item in payload["items"]
    ]
    rows += _pages(payload, "history:page")
    rows += [
        [InlineKeyboardButton(text="📎 Вся история (ZIP/CSV)", callback_data="history:export")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"history:page:{payload['page']}")],
        [InlineKeyboardButton(text="⬅️ Главная", callback_data="nav:dashboard")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def detail_keyboard(payload: dict[str, Any]) -> InlineKeyboardMarkup:
    item = payload["position"]
    rows = [
        [
            InlineKeyboardButton(text="Solscan", url=f"https://solscan.io/token/{item['mint']}"),
            InlineKeyboardButton(
                text="График", url=f"https://dexscreener.com/solana/{item['mint']}"
            ),
        ]
    ]
    rows += _pages(payload, f"history:coin:{item['id']}")
    rows += [[InlineKeyboardButton(text="⬅️ Вся история", callback_data="history:page:0")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _pages(payload: dict[str, Any], prefix: str) -> list[list[InlineKeyboardButton]]:
    buttons = []
    if payload["page"] > 0:
        buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:{payload['page'] - 1}")
        )
    if payload["page"] + 1 < payload["pages"]:
        buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:{payload['page'] + 1}")
        )
    return [buttons] if buttons else []
