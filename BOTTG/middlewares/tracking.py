# middlewares/tracking.py
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from db.database import db


class ActivityMiddleware(BaseMiddleware):
    """
    Обновляет last_active_at на каждый апдейт.
    Автоматически регистрирует новых пользователей.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user and not user.is_bot:
            existing = await db.get_user(user.id)
            if existing:
                await db.update_activity(user.id)
            else:
                await db.add_user(user.id, user.username, user.first_name)
        return await handler(event, data)