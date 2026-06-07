import asyncio
import logging
import platform
import sys
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.core.loader import bot
from bot.db.repositories import UserRepository, SessionRepository, ModuleRepository, QuestionRepository
from bot.utils.states import AdminBroadcastStates

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


def admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Modullar", callback_data="admin:modules")
    builder.button(text="👥 Foydalanuvchilar", callback_data="admin:users")
    builder.button(text="📊 Statistika", callback_data="admin:stats")
    builder.button(text="ℹ️ Bot ma'lumotlari", callback_data="admin:botinfo")
    builder.button(text="📢 Reklama yuborish", callback_data="admin:broadcast")
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Ruxsat yo'q.")
        return
    await message.answer(
        "👨‍💼 <b>Admin Panel</b>\n\nBoshqaruv bo'limini tanlang:",
        reply_markup=admin_main_kb(),
    )


@router.callback_query(F.data == "admin:main")
async def admin_main(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await callback.message.edit_text(
        "👨‍💼 <b>Admin Panel</b>\n\nBoshqaruv bo'limini tanlang:",
        reply_markup=admin_main_kb(),
    )


# ── Statistika ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return

    user_repo = UserRepository(session)
    session_repo = SessionRepository(session)

    total_users = await user_repo.count()
    recent = await session_repo.get_recent(50)

    completed = len(recent)
    avg_iq = sum(s.iq_score for s in recent if s.iq_score) / completed if completed else 0
    avg_score = sum(s.score for s in recent if s.score is not None) / completed if completed else 0

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="admin:main")

    await callback.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n\n"
        f"📝 So'nggi 50 yakunlangan test:\n"
        f"  ✅ O'rtacha to'g'ri: <b>{avg_score:.1f}/30</b>\n"
        f"  🧠 O'rtacha IQ: <b>{avg_iq:.0f}</b>",
        reply_markup=builder.as_markup(),
    )


# ── Bot ma'lumotlari ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:botinfo")
async def admin_botinfo(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return

    me = await bot.get_me()
    user_repo = UserRepository(session)
    module_repo = ModuleRepository(session)
    q_repo = QuestionRepository(session)
    session_repo = SessionRepository(session)

    total_users = await user_repo.count()
    modules = await module_repo.get_all()
    total_sessions = await session_repo.get_recent(9999)

    module_lines = []
    for m in modules:
        cnt = await q_repo.count_by_module(m.id)
        status = "✅" if m.is_active else "❌"
        module_lines.append(f"  {status} {m.name} — {cnt} ta savol")

    py_ver = sys.version.split()[0]
    os_info = f"{platform.system()} {platform.release()}"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="admin:main")

    await callback.message.edit_text(
        f"ℹ️ <b>Bot ma'lumotlari</b>\n\n"
        f"🤖 Bot: @{me.username} (<code>{me.id}</code>)\n"
        f"📛 Ism: {me.full_name}\n\n"
        f"👥 Foydalanuvchilar: <b>{total_users}</b>\n"
        f"📝 Yakunlangan testlar: <b>{len([s for s in total_sessions if s.finished_at])}</b>\n\n"
        f"📦 <b>Modullar ({len(modules)} ta):</b>\n"
        + "\n".join(module_lines) +
        f"\n\n🖥 Server: {os_info}\n"
        f"🐍 Python: {py_ver}",
        reply_markup=builder.as_markup(),
    )


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminBroadcastStates.waiting_message)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor", callback_data="admin:main")
    await callback.message.edit_text(
        "📢 <b>Reklama / E'lon yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing.\n"
        "Matn, rasm, video yoki har qanday turdagi xabar bo'lishi mumkin.",
        reply_markup=builder.as_markup(),
    )


@router.message(AdminBroadcastStates.waiting_message)
async def broadcast_preview(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(preview_msg_id=message.message_id, chat_id=message.chat.id)
    await state.set_state(AdminBroadcastStates.waiting_confirm)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yuborish", callback_data="admin:broadcast:confirm")
    builder.button(text="❌ Bekor", callback_data="admin:broadcast:cancel")
    builder.adjust(2)
    await message.answer(
        "👆 Yuqoridagi xabar barcha foydalanuvchilarga yuboriladi.\nTasdiqlaysizmi?",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "admin:broadcast:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Reklama bekor qilindi.", reply_markup=_back_kb())


@router.callback_query(F.data == "admin:broadcast:confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    data = await state.get_data()
    await state.clear()

    user_repo = UserRepository(session)
    user_ids = await user_repo.get_all_ids()

    src_chat = data["chat_id"]
    src_msg = data["preview_msg_id"]

    await callback.message.edit_text(f"⏳ Yuborilmoqda... ({len(user_ids)} ta user)")

    sent = blocked = failed = 0
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=src_chat, message_id=src_msg)
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err or "not found" in err:
                blocked += 1
            else:
                failed += 1
        await asyncio.sleep(0.05)  # flood control

    await callback.message.answer(
        f"📢 <b>Reklama yuborildi!</b>\n\n"
        f"✅ Yuborildi: {sent}\n"
        f"🚫 Bloklagan: {blocked}\n"
        f"❌ Xato: {failed}",
        reply_markup=_back_kb(),
    )


def _back_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Admin panel", callback_data="admin:main")
    return builder.as_markup()
