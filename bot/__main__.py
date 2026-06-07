import asyncio
import logging

from aiogram import Dispatcher
from aiogram.types import BotCommand

from bot.core.config import settings
from bot.core.loader import bot, dp, redis_client
from bot.db.base import create_tables
from bot.db.models import User, Module, Question, TestSession  # noqa
from scripts.seed import seed_if_empty
from bot.middlewares import DbSessionMiddleware
from bot.middlewares.error_handler import router as error_router
from bot.handlers.user import start as user_start
from bot.handlers.user import test as user_test
from bot.handlers.user import feedback as user_feedback
from bot.handlers.admin import main as admin_main
from bot.handlers.admin import modules as admin_modules
from bot.handlers.admin import questions as admin_questions
from bot.handlers.admin import users as admin_users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(error_router)
    dp.include_router(user_start.router)
    dp.include_router(user_test.router)
    dp.include_router(user_feedback.router)
    dp.include_router(admin_main.router)
    dp.include_router(admin_modules.router)
    dp.include_router(admin_questions.router)
    dp.include_router(admin_users.router)


async def set_commands() -> None:
    from aiogram.types import BotCommandScopeDefault, BotCommandScopeChat

    user_commands = [
        BotCommand(command="start", description="Botni boshlash"),
        BotCommand(command="feedback", description="Fikr-mulohaza yuborish"),
    ]
    admin_commands = user_commands + [
        BotCommand(command="admin", description="Admin panel"),
    ]

    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception:
            pass


async def main() -> None:
    logger.info("Starting IQ Bot...")
    await create_tables()
    logger.info("Database tables ready.")
    await seed_if_empty()

    dp.update.middleware(DbSessionMiddleware())
    register_routers(dp)
    await set_commands()

    logger.info("Bot polling started.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await redis_client.aclose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
