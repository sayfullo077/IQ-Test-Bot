import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.core.loader import bot
from bot.db.repositories import UserRepository, SessionRepository
from bot.db.repositories.user_repo import PAGE_SIZE
from bot.utils.states import AdminUserStates

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


# ── Keyboards ─────────────────────────────────────────────────────────────────

def users_list_kb(users, page: int, total: int):
    builder = InlineKeyboardBuilder()
    for u in users:
        status = "🚫" if u.is_banned else "👤"
        name = u.full_name[:20]
        builder.button(text=f"{status} {name}", callback_data=f"admin:user:{u.id}")
    builder.adjust(1)

    nav = []
    if page > 0:
        nav.append(("◀️ Oldingi", f"admin:users:page:{page - 1}"))
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    if (page + 1) < total_pages:
        nav.append(("Keyingi ▶️", f"admin:users:page:{page + 1}"))
    for label, cb in nav:
        builder.button(text=label, callback_data=cb)
    builder.button(text="🔙 Orqaga", callback_data="admin:main")
    if nav:
        builder.adjust(1, len(nav), 1)
    else:
        builder.adjust(1)
    return builder.as_markup()


def user_detail_kb(user):
    builder = InlineKeyboardBuilder()
    if user.is_banned:
        builder.button(text="✅ Banni olib tashlash", callback_data=f"admin:user:unban:{user.id}")
    else:
        builder.button(text="🚫 Banlash", callback_data=f"admin:user:ban:{user.id}")
    builder.button(text="💬 Xabar yuborish", callback_data=f"admin:user:msg:{user.id}")
    builder.button(text="👁 Profilni tekshirish", callback_data=f"admin:user:profile:{user.id}")
    builder.button(text="🗑 O'chirish", callback_data=f"admin:user:delete:{user.id}")
    builder.button(text="🔙 Orqaga", callback_data="admin:users:page:0")
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete_user_kb(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data=f"admin:user:confirm_delete:{user_id}")
    builder.button(text="❌ Bekor", callback_data=f"admin:user:{user_id}")
    builder.adjust(2)
    return builder.as_markup()


# ── List ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:users")
async def users_page_0(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await _show_users_page(callback, session, 0)


@router.callback_query(F.data.startswith("admin:users:page:"))
async def users_page(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    page = int(callback.data.split(":")[3])
    await _show_users_page(callback, session, page)


async def _show_users_page(callback: CallbackQuery, session: AsyncSession, page: int):
    repo = UserRepository(session)
    users = await repo.get_page(page)
    total = await repo.count()

    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    await callback.message.edit_text(
        f"👥 <b>Foydalanuvchilar</b>  ({total} ta)\n"
        f"Sahifa: {page + 1}/{max(total_pages, 1)}",
        reply_markup=users_list_kb(users, page, total),
    )


# ── Detail ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^admin:user:\d+$"))
async def user_detail(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[2])
    await _show_user_detail(callback, session, user_id)


async def _show_user_detail(callback: CallbackQuery, session: AsyncSession, user_id: int):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    sess_repo = SessionRepository(session)
    sessions = await sess_repo.get_user_sessions(user.id)
    finished = [s for s in sessions if s.finished_at]
    best_iq = max((s.iq_score for s in finished if s.iq_score), default=None)
    avg_score = (
        sum(s.score for s in finished if s.score is not None) / len(finished)
        if finished else None
    )

    uname = f"@{user.username}" if user.username else "—"
    status = "🚫 Banlangan" if user.is_banned else "✅ Faol"
    reg_date = user.created_at.strftime("%d.%m.%Y")
    last = user.last_seen.strftime("%d.%m.%Y %H:%M")

    score_line = f"📈 O'rtacha to'g'ri: <b>{avg_score:.1f}/30</b>" if avg_score else ""
    await callback.message.edit_text(
        f"👤 <b>{user.full_name}</b>\n\n"
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"📛 Username: {uname}\n"
        f"📅 Ro'yxatdan: {reg_date}\n"
        f"🕐 Oxirgi faollik: {last}\n"
        f"🔘 Status: {status}\n\n"
        f"📊 Testlar: <b>{len(finished)}</b> ta yakunlangan\n"
        f"🧠 Eng yuqori IQ: <b>{best_iq or '—'}</b>\n"
        + score_line,
        reply_markup=user_detail_kb(user),
    )


# ── Ban / Unban ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:user:ban:"))
async def ban_user(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[3])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user:
        await repo.ban(user)
    await callback.answer("🚫 Foydalanuvchi banlandi.")
    await _show_user_detail(callback, session, user_id)


@router.callback_query(F.data.startswith("admin:user:unban:"))
async def unban_user(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[3])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user:
        await repo.unban(user)
    await callback.answer("✅ Ban olib tashlandi.")
    await _show_user_detail(callback, session, user_id)


# ── Send message ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:user:msg:"))
async def send_msg_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[3])
    await state.set_state(AdminUserStates.sending_message)
    await state.update_data(target_user_id=user_id)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor", callback_data=f"admin:user:{user_id}")
    await callback.message.edit_text(
        "✍️ Foydalanuvchiga yuboriladigan xabarni yozing:",
        reply_markup=builder.as_markup(),
    )


@router.message(AdminUserStates.sending_message)
async def send_msg_execute(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()

    repo = UserRepository(session)
    user = await repo.get_by_id(data["target_user_id"])
    if not user:
        await message.answer("Foydalanuvchi topilmadi.")
        return
    try:
        await bot.send_message(
            user.telegram_id,
            f"📬 <b>Admin xabari:</b>\n\n{message.text}",
        )
        await message.answer(f"✅ Xabar yuborildi → {user.full_name}")
    except Exception as e:
        await message.answer(f"⚠️ Yuborib bo'lmadi: {e}")


# ── Get profile ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:user:profile:"))
async def get_profile(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[3])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    try:
        chat = await bot.get_chat(user.telegram_id)
        has_photo = "✅ Bor" if chat.photo else "❌ Yo'q"
        bio = chat.bio or "—"
        uname_link = f"tg://user?id={user.telegram_id}"
        lines = [
            f"👤 <b>{chat.full_name}</b>",
            f"🆔 ID: <code>{user.telegram_id}</code>",
            f"📛 Username: @{chat.username}" if chat.username else "📛 Username: —",
            f"🖼 Profil rasmi: {has_photo}",
            f"📝 Bio: {bio}",
            f"🔗 Profil: <a href='{uname_link}'>Ochish</a>",
        ]
        await callback.answer("\n".join(lines[:3]), show_alert=True)
    except Exception as e:
        await callback.answer(f"Ma'lumot olishda xato: {e}", show_alert=True)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:user:delete:"))
async def delete_user_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[3])
    await callback.message.edit_text(
        "⚠️ Foydalanuvchini o'chirishni tasdiqlaysizmi?\n"
        "<b>Barcha test natijalari ham o'chib ketadi!</b>",
        reply_markup=confirm_delete_user_kb(user_id),
    )


@router.callback_query(F.data.startswith("admin:user:confirm_delete:"))
async def delete_user_execute(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[3])
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user:
        await repo.delete(user)
    await callback.answer("✅ O'chirildi.")
    await _show_users_page(callback, session, 0)
