from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from bot.core.config import settings


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None

        if user_id not in settings.ADMIN_IDS:
            if isinstance(event, Message):
                await event.answer("⛔ Ruxsat yo'q.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Ruxsat yo'q.", show_alert=True)
            return
        return await handler(event, data)
