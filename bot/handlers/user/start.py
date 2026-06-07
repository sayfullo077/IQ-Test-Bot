from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import UserRepository, SessionRepository, ModuleRepository
from bot.keyboards.user_kb import main_menu_keyboard, modules_keyboard
from bot.services.test_service import TestService
from bot.core.loader import redis_client

router = Router()


async def _safe_edit(callback: CallbackQuery, text: str, **kwargs):
    try:
        await callback.message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    repo = UserRepository(session)
    user, is_new = await repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    if user.is_banned:
        await message.answer("🚫 Siz botdan bloklangansiz.")
        return

    greeting = "Xush kelibsiz" if is_new else "Qayta xush kelibsiz"
    await message.answer(
        f"👋 <b>{greeting}, {message.from_user.first_name}!</b>\n\n"
        "🧠 <b>IQ Test Bot</b> — intellektual qobiliyatingizni aniqlang.\n\n"
        "📦 3 ta modul mavjud, har birida 30 ta savol.\n"
        "🖼 Har bir savolda rasm ko'rsatiladi.\n"
        "⏱ Har savol uchun 60 soniya vaqt beriladi.\n"
        "🔘 A/B/C/D/E/F tugmalaridan birini bosib javob bering.\n\n"
        "💬 Savol yoki taklif bo'lsa — /feedback",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "open_modules")
async def show_modules(callback: CallbackQuery, session: AsyncSession):
    repo = ModuleRepository(session)
    modules = await repo.get_all(active_only=True)
    if not modules:
        await callback.answer("Hozircha faol modullar yo'q.", show_alert=True)
        return
    await _safe_edit(
        callback,
        "📚 <b>Mavjud modullar:</b>\n\nTestni boshlash uchun modulni tanlang:",
        reply_markup=modules_keyboard(modules),
    )


@router.callback_query(F.data == "my_results")
async def show_my_results(callback: CallbackQuery, session: AsyncSession):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    session_repo = SessionRepository(session)
    sessions = await session_repo.get_user_sessions(user.id)
    finished = [s for s in sessions if s.finished_at]

    if not finished:
        await _safe_edit(
            callback,
            "📊 Siz hali hech qanday test yakunlamadingiz.\n\nBotni sinab ko'ring!",
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer()
        return

    module_repo = ModuleRepository(session)
    lines = ["📊 <b>Mening natijalarim:</b>\n"]
    for s in finished[:10]:
        module = await module_repo.get_by_id(s.module_id)
        module_name = module.name if module else f"Modul #{s.module_id}"
        date_str = s.finished_at.strftime("%d.%m.%Y %H:%M") if s.finished_at else "—"
        lines.append(
            f"🔹 <b>{module_name}</b>\n"
            f"   📅 {date_str}\n"
            f"   ✅ {s.score}/30 to'g'ri | IQ: <b>{s.iq_score}</b>"
        )

    await _safe_edit(
        callback,
        "\n\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_test")
async def cancel_test(callback: CallbackQuery):
    test_svc = TestService(redis_client)
    await test_svc.finish(callback.from_user.id)
    await _safe_edit(
        callback,
        "❌ Test bekor qilindi.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
