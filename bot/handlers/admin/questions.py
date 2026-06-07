from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import QuestionRepository, ModuleRepository
from bot.keyboards.admin_kb import (
    questions_list_keyboard,
    question_detail_keyboard,
    confirm_delete_keyboard,
    cancel_keyboard,
)
from bot.utils.states import AdminQuestionStates
from bot.core.config import settings

router = Router()

OPTIONS_LETTERS = ["A", "B", "C", "D", "E", "F"]


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


# ── List questions ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:questions:"))
async def list_questions(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[2])
    q_repo = QuestionRepository(session)
    questions = await q_repo.get_by_module(module_id)

    m_repo = ModuleRepository(session)
    module = await m_repo.get_by_id(module_id)
    name = module.name if module else f"#{module_id}"

    await callback.message.edit_text(
        f"📝 <b>{name}</b> — Savollar ({len(questions)}/30):",
        reply_markup=questions_list_keyboard(module_id, questions),
    )


# ── Question detail ───────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^admin:question:\d+$"))
async def question_detail(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    question_id = int(callback.data.split(":")[2])
    q_repo = QuestionRepository(session)
    question = await q_repo.get_by_id(question_id)
    if not question:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return

    opts = " / ".join(OPTIONS_LETTERS[:question.options_count])
    has_img = "✅" if (question.image_file_id or question.image_path) else "❌"
    await callback.message.edit_text(
        f"📋 <b>Savol #{question.order}</b>\n\n"
        f"🏷 Turi: {question.q_type or '—'}\n"
        f"⚡ Qiyinlik: {question.difficulty or '—'}\n"
        f"📊 Variantlar: {opts}\n"
        f"✅ To'g'ri javob: <b>{question.correct_answer}</b>\n"
        f"🖼 Rasm: {has_img}",
        reply_markup=question_detail_keyboard(question),
    )


# ── Create question ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:question:create:"))
async def create_question_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[3])
    await state.set_state(AdminQuestionStates.waiting_image)
    await state.update_data(module_id=module_id, creating=True)
    await callback.message.edit_text(
        "🖼 Savol rasmini yuboring (foto yoki fayl sifatida):",
        reply_markup=cancel_keyboard(f"admin:questions:{module_id}"),
    )


@router.message(AdminQuestionStates.waiting_image, F.photo | F.document)
async def receive_image(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type and "image" in message.document.mime_type:
        file_id = message.document.file_id
    else:
        await message.answer("❌ Iltimos, rasm yuboring.")
        return

    data = await state.get_data()

    if data.get("editing"):
        # Editing existing question image
        q_repo = QuestionRepository(session)
        question = await q_repo.get_by_id(data["question_id"])
        if question:
            await q_repo.update(question, image_file_id=file_id, image_path=None)
        await state.clear()
        await message.answer("✅ Rasm yangilandi.", reply_markup=question_detail_keyboard(question))
        return

    # Creating new question
    await state.update_data(image_file_id=file_id)
    await state.set_state(AdminQuestionStates.waiting_options_count)
    module_id = data.get("module_id")
    await message.answer(
        "🔢 Variantlar sonini tanlang:",
        reply_markup=_options_count_keyboard(module_id),
    )


@router.callback_query(F.data.startswith("admin:set_options:"), AdminQuestionStates.waiting_options_count)
async def set_options_count(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    count = int(callback.data.split(":")[2])
    data = await state.get_data()

    if data.get("editing_options"):
        # Editing existing question options count
        q_repo = QuestionRepository(session)
        question = await q_repo.get_by_id(data["question_id"])
        if question:
            await q_repo.update(question, options_count=count)
        await state.clear()
        await callback.message.edit_text(
            f"✅ Variantlar soni yangilandi: <b>{count}</b>",
            reply_markup=question_detail_keyboard(question),
        )
        return

    # Creating new question
    await state.update_data(options_count=count)
    await state.set_state(AdminQuestionStates.waiting_correct_answer)
    opts = " / ".join(OPTIONS_LETTERS[:count])
    await callback.message.edit_text(
        f"✅ To'g'ri javobni kiriting ({opts}):",
        reply_markup=_answer_input_keyboard(count),
    )


@router.callback_query(F.data.startswith("admin:set_answer:"), AdminQuestionStates.waiting_correct_answer)
async def set_answer(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    answer = callback.data.split(":")[2].upper()
    data = await state.get_data()

    if data.get("editing_answer"):
        # Editing existing question answer
        from bot.db.base import async_session_maker
        async with async_session_maker() as session:
            async with session.begin():
                from bot.db.repositories import QuestionRepository
                q_repo = QuestionRepository(session)
                question = await q_repo.get_by_id(data["question_id"])
                if question:
                    await q_repo.update(question, correct_answer=answer)
        await state.clear()
        await callback.message.edit_text(f"✅ To'g'ri javob yangilandi: <b>{answer}</b>")
        return

    # Creating new question
    await state.update_data(correct_answer=answer)
    await state.set_state(AdminQuestionStates.waiting_type)
    await callback.message.edit_text(
        "🏷 Savol turini kiriting (masalan: Matrix, Series, Analogy, /skip):"
    )


@router.message(AdminQuestionStates.waiting_type)
async def set_type(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    q_type = None if message.text.strip() == "/skip" else message.text.strip()
    await state.update_data(q_type=q_type)
    await state.set_state(AdminQuestionStates.waiting_difficulty)
    await message.answer("⚡ Qiyinlik darajasini kiriting (Easy/Medium/Hard yoki /skip):")


@router.message(AdminQuestionStates.waiting_difficulty)
async def set_difficulty(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    difficulty = None if message.text.strip() == "/skip" else message.text.strip()
    data = await state.get_data()

    q_repo = QuestionRepository(session)
    # Determine order
    existing = await q_repo.get_by_module(data["module_id"])
    order = max((q.order for q in existing), default=0) + 1

    question = await q_repo.create(
        module_id=data["module_id"],
        order=order,
        correct_answer=data["correct_answer"],
        options_count=data["options_count"],
        image_file_id=data.get("image_file_id"),
        q_type=data.get("q_type"),
        difficulty=difficulty,
    )
    await state.clear()
    await message.answer(
        f"✅ Savol #{order} yaratildi!\n"
        f"To'g'ri javob: <b>{question.correct_answer}</b>",
        reply_markup=question_detail_keyboard(question),
    )


# ── Edit image ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:question:edit_image:"))
async def edit_image_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    question_id = int(callback.data.split(":")[3])
    await state.set_state(AdminQuestionStates.waiting_image)
    await state.update_data(question_id=question_id, editing=True)
    await callback.message.edit_text(
        "🖼 Yangi rasmni yuboring:",
        reply_markup=cancel_keyboard(f"admin:question:{question_id}"),
    )




# ── Edit correct answer ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:question:edit_answer:"))
async def edit_answer_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    question_id = int(callback.data.split(":")[3])
    q_repo = QuestionRepository(session)
    question = await q_repo.get_by_id(question_id)
    if not question:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return
    await state.set_state(AdminQuestionStates.waiting_correct_answer)
    await state.update_data(question_id=question_id, editing_answer=True)
    await callback.message.edit_text(
        f"✅ Yangi to'g'ri javobni tanlang (hozir: <b>{question.correct_answer}</b>):",
        reply_markup=_answer_input_keyboard(question.options_count),
    )



# ── Edit options count ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:question:edit_options:"))
async def edit_options_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    question_id = int(callback.data.split(":")[3])
    await state.set_state(AdminQuestionStates.waiting_options_count)
    await state.update_data(question_id=question_id, editing_options=True)
    await callback.message.edit_text(
        "🔢 Yangi variantlar sonini tanlang:",
        reply_markup=_options_count_keyboard(None),
    )




# ── Delete question ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:question:delete:"))
async def delete_question_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    question_id = int(callback.data.split(":")[3])
    await callback.message.edit_text(
        "⚠️ Haqiqatan ham bu savolni o'chirmoqchimisiz?",
        reply_markup=confirm_delete_keyboard("question", question_id),
    )


@router.callback_query(F.data.startswith("admin:confirm_delete:question:"))
async def delete_question_execute(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    question_id = int(callback.data.split(":")[3])
    q_repo = QuestionRepository(session)
    question = await q_repo.get_by_id(question_id)
    module_id = question.module_id if question else None
    if question:
        await q_repo.delete(question)
    await callback.answer("✅ Savol o'chirildi.")

    if module_id:
        questions = await q_repo.get_by_module(module_id)
        await callback.message.edit_text(
            f"📝 Savollar ro'yxati:",
            reply_markup=questions_list_keyboard(module_id, questions),
        )


# ── Helper keyboards ──────────────────────────────────────────────────────────

def _options_count_keyboard(module_id: int | None):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for n in [4, 5, 6]:
        builder.button(text=str(n), callback_data=f"admin:set_options:{n}")
    if module_id:
        builder.button(text="❌ Bekor qilish", callback_data=f"admin:questions:{module_id}")
    builder.adjust(3)
    return builder.as_markup()


def _answer_input_keyboard(options_count: int):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for letter in OPTIONS_LETTERS[:options_count]:
        builder.button(text=letter, callback_data=f"admin:set_answer:{letter}")
    builder.adjust(options_count)
    return builder.as_markup()
