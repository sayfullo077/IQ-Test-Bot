import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.base import async_session_maker
from bot.db.repositories import (
    UserRepository,
    ModuleRepository,
    QuestionRepository,
    SessionRepository,
)
from bot.keyboards.user_kb import (
    answer_keyboard,
    confirm_start_keyboard,
    main_menu_keyboard,
)
from bot.services.test_service import TestService, ActiveTest, QUESTION_TIME_LIMIT
from bot.services.iq_calculator import calculate_iq, iq_full_result
from bot.core.loader import redis_client

logger = logging.getLogger(__name__)
router = Router()


def _caption(index: int, total: int, remaining: int) -> str:
    bar = "▓" * (index) + "░" * (total - index)
    return f"<b>{index + 1}/{total}</b>  ⏱ {remaining}s\n{bar}"


async def _send_question(
    callback: CallbackQuery,
    question,
    index: int,
    total: int,
    remaining: int,
    edit: bool = False,
) -> str | None:
    """Send/edit question photo. Returns new file_id if uploaded fresh."""
    caption = _caption(index, total, remaining)
    kb = answer_keyboard(question.options_count, question.id)

    if question.image_file_id:
        photo = question.image_file_id
    elif question.image_path:
        photo = FSInputFile(question.image_path)
    else:
        await callback.message.edit_text(
            f"⚠️ Savol #{index + 1} uchun rasm topilmadi. Test to'xtatildi.",
            reply_markup=main_menu_keyboard(),
        )
        return None

    try:
        if edit and callback.message.photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML"),
                reply_markup=kb,
            )
            return None
        else:
            await callback.message.delete()
            msg = await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb)
            if not question.image_file_id and msg.photo:
                return msg.photo[-1].file_id
    except Exception as e:
        logger.error(f"Error sending question: {e}")
    return None


@router.callback_query(F.data.startswith("start_module:"))
async def start_module(callback: CallbackQuery, session: AsyncSession):
    module_id = int(callback.data.split(":")[1])
    module_repo = ModuleRepository(session)
    module = await module_repo.get_by_id(module_id)
    if not module or not module.is_active:
        await callback.answer("Bu modul mavjud emas.", show_alert=True)
        return

    q_repo = QuestionRepository(session)
    count = await q_repo.count_by_module(module_id)

    test_svc = TestService(redis_client)
    has_active = await test_svc.has_active(callback.from_user.id)
    note = "\n\n⚠️ <b>Diqqat:</b> Faol test bor. Yangi test boshlasangiz, avvalgisi bekor bo'ladi." if has_active else ""

    await callback.message.edit_text(
        f"📦 <b>{module.name}</b>\n\n"
        f"{module.description or ''}\n\n"
        f"📊 Savollar: <b>{count} ta</b>\n"
        f"⏱ Har bir savolga: <b>{QUESTION_TIME_LIMIT} soniya</b>\n"
        f"⌚ Jami vaqt: ~<b>{count * QUESTION_TIME_LIMIT // 60} daqiqa</b>"
        f"{note}",
        reply_markup=confirm_start_keyboard(module_id),
    )


@router.callback_query(F.data.startswith("confirm_start:"))
async def confirm_start(callback: CallbackQuery, session: AsyncSession):
    module_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
    )

    if user.is_banned:
        await callback.answer("Siz botdan bloklangansiz.", show_alert=True)
        return

    module_repo = ModuleRepository(session)
    module = await module_repo.get_by_id(module_id)
    if not module or not module.is_active:
        await callback.answer("Bu modul mavjud emas.", show_alert=True)
        return

    q_repo = QuestionRepository(session)
    questions = await q_repo.get_by_module(module_id)
    if not questions:
        await callback.answer("Bu modulda savollar yo'q.", show_alert=True)
        return

    session_repo = SessionRepository(session)
    test_session = await session_repo.create(user_id=user.id, module_id=module_id)

    test_svc = TestService(redis_client)
    active = ActiveTest(
        session_id=test_session.id,
        module_id=module_id,
        question_ids=[q.id for q in questions],
    )
    await test_svc.start(callback.from_user.id, active)
    await callback.answer("Test boshlandi! ✅")

    new_file_id = await _send_question(
        callback, questions[0], 0, len(questions), QUESTION_TIME_LIMIT, edit=False
    )
    if new_file_id:
        async with async_session_maker() as s:
            async with s.begin():
                qr = QuestionRepository(s)
                q = await qr.get_by_id(questions[0].id)
                if q:
                    await qr.cache_file_id(q, new_file_id)


@router.callback_query(F.data.startswith("answer:"))
async def handle_answer(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    question_id = int(parts[1])
    chosen = parts[2].upper()

    test_svc = TestService(redis_client)
    active = await test_svc.get(callback.from_user.id)

    if not active:
        await callback.answer("Faol test topilmadi. /start bosing.", show_alert=True)
        return

    if active.current_question_id != question_id:
        await callback.answer("Bu savol allaqachon o'tilgan.", show_alert=True)
        return

    timed_out_this = active.is_timed_out
    if timed_out_this:
        active.record_timeout(question_id)
        await callback.answer("⏰ Vaqt tugadi! Keyingi savolga o'tildi.", show_alert=False)
    else:
        active.record_answer(question_id, chosen)
        await callback.answer()

    if active.is_finished:
        q_repo = QuestionRepository(session)
        correct = 0
        timed_out_count = 0
        for qid_str, ans in active.answers.items():
            if ans == "TIMEOUT":
                timed_out_count += 1
                continue
            q = await q_repo.get_by_id(int(qid_str))
            if q and q.correct_answer.upper() == ans.upper():
                correct += 1

        iq = calculate_iq(correct, active.total)
        result_text = iq_full_result(iq, correct, active.total, timed_out_count)

        session_repo = SessionRepository(session)
        test_s = await session_repo.get_by_id(active.session_id)
        if test_s:
            await session_repo.finish(test_s, correct, iq, active.answers)

        await test_svc.finish(callback.from_user.id)

        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(result_text, reply_markup=main_menu_keyboard())
        return

    await test_svc.save(callback.from_user.id, active)

    q_repo = QuestionRepository(session)
    next_q = await q_repo.get_by_id(active.current_question_id)
    if not next_q:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return

    new_file_id = await _send_question(
        callback,
        next_q,
        active.current_index,
        active.total,
        active.remaining_seconds,
        edit=True,
    )
    if new_file_id:
        async with async_session_maker() as s:
            async with s.begin():
                qr = QuestionRepository(s)
                q = await qr.get_by_id(next_q.id)
                if q:
                    await qr.cache_file_id(q, new_file_id)
