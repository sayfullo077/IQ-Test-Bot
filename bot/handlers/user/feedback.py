"""
/feedback — user bot haqida xabar yuboradi, admin anonim ko'radi va javob bera oladi.
Anonimlik: admin faqat display name ko'radi, user ID faqat Redis da saqlanadi.
"""
import json
import logging
import uuid
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.core.config import settings
from bot.core.loader import bot, redis_client
from bot.utils.states import FeedbackStates, AdminReplyStates

logger = logging.getLogger(__name__)
router = Router()

FB_PREFIX = "fb:"


async def _save_fb(fid: str, user_id: int, name: str) -> None:
    await redis_client.set(
        f"{FB_PREFIX}{fid}",
        json.dumps({"user_id": user_id, "name": name}),
        ex=3600 * 48,
    )


async def _get_fb(fid: str) -> dict | None:
    raw = await redis_client.get(f"{FB_PREFIX}{fid}")
    return json.loads(raw) if raw else None


def _admin_reply_kb(fid: str):
    b = InlineKeyboardBuilder()
    b.button(text="↩️ Javob berish", callback_data=f"admin_reply:{fid}")
    return b.as_markup()


def _user_reply_kb(fid: str):
    b = InlineKeyboardBuilder()
    b.button(text="↩️ Javob berish", callback_data=f"user_reply:{fid}")
    return b.as_markup()


# ── User: /feedback ───────────────────────────────────────────────────────────

@router.message(Command("feedback"))
async def cmd_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_message)
    await message.answer(
        "💬 <b>Feedback</b>\n\n"
        "Bot haqida fikr, xato yoki taklif yuboring.\n"
        "Xabaringiz adminlarga <b>anonim</b> yuboriladi.\n\n"
        "✍️ Xabaringizni yozing:"
    )


@router.message(FeedbackStates.waiting_message)
async def receive_feedback(message: Message, state: FSMContext):
    await state.clear()
    fid = uuid.uuid4().hex[:12]
    uid = message.from_user.id
    name = message.from_user.first_name

    await _save_fb(fid, uid, name)

    sent = False
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📩 <b>Yangi feedback</b>\n\n"
                f"👤 Foydalanuvchi: <b>{name}</b>\n\n"
                f"💬 {message.text}",
                reply_markup=_admin_reply_kb(fid),
            )
            sent = True
        except Exception as e:
            logger.warning(f"Admin {admin_id}: {e}")

    if sent:
        await message.answer("✅ Xabaringiz yuborildi. Tez orada javob beramiz!")
    else:
        await message.answer("⚠️ Hozircha adminlarga yetib borishi mumkin emas.")


# ── User: reply to admin ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_reply:"))
async def user_reply_start(callback: CallbackQuery, state: FSMContext):
    fid = callback.data.split(":")[1]
    await state.set_state(FeedbackStates.waiting_reply)
    await state.update_data(fid=fid)
    await callback.message.answer("✍️ Javobingizni yozing:")
    await callback.answer()


@router.message(FeedbackStates.waiting_reply)
async def user_reply_send(message: Message, state: FSMContext):
    data = await state.get_data()
    fid = data.get("fid", "")
    await state.clear()

    name = message.from_user.first_name
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"↩️ <b>Foydalanuvchi javobi</b>\n\n"
                f"👤 {name}\n\n"
                f"💬 {message.text}",
                reply_markup=_admin_reply_kb(fid),
            )
        except Exception as e:
            logger.warning(f"Admin {admin_id}: {e}")

    await message.answer("✅ Javobingiz yuborildi.")


# ── Admin: reply to feedback ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_reply:"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    fid = callback.data.split(":")[1]
    meta = await _get_fb(fid)
    if not meta:
        await callback.answer("Bu feedback eskirgan (48 soatdan o'tgan).", show_alert=True)
        return

    await state.set_state(AdminReplyStates.waiting_reply)
    await state.update_data(fid=fid, target_uid=meta["user_id"])
    await callback.message.answer(f"✍️ <b>{meta['name']}</b> ga javob yozing:")
    await callback.answer()


@router.message(AdminReplyStates.waiting_reply)
async def admin_reply_send(message: Message, state: FSMContext):
    data = await state.get_data()
    fid = data.get("fid", "")
    target_uid = data.get("target_uid")
    await state.clear()

    try:
        await bot.send_message(
            target_uid,
            f"📬 <b>Admin javobi:</b>\n\n{message.text}",
            reply_markup=_user_reply_kb(fid),
        )
        await message.answer("✅ Javob yuborildi.")
    except Exception as e:
        await message.answer(f"⚠️ Yuborib bo'lmadi: {e}")
