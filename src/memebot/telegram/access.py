from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AllowlistMiddleware(BaseMiddleware):
    def __init__(self, allowed_user_ids: frozenset[int]) -> None:
        self._allowed_user_ids = allowed_user_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = _user_id(event)
        if is_allowed_user(user_id, self._allowed_user_ids):
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            await event.answer(
                "Access denied. Use /whoami to get your numeric ID.", show_alert=True
            )
        elif isinstance(event, Message):
            await event.answer("Access denied. Use /whoami and add your ID to the allowlist.")
        return None


def _user_id(event: TelegramObject) -> int | None:
    if isinstance(event, (Message, CallbackQuery)) and event.from_user is not None:
        return event.from_user.id
    return None


def is_allowed_user(user_id: int | None, allowed_user_ids: frozenset[int]) -> bool:
    return user_id is not None and user_id in allowed_user_ids
