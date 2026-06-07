from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import ModuleRepository
from bot.keyboards.admin_kb import (
    modules_list_keyboard,
    module_detail_keyboard,
    confirm_delete_keyboard,
    cancel_keyboard,
)
from bot.keyboards.admin_kb import admin_main_keyboard
from bot.utils.states import AdminModuleStates
from bot.core.config import settings

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


# ── List modules ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:modules")
async def list_modules(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    repo = ModuleRepository(session)
    modules = await repo.get_all()
    await callback.message.edit_text(
        "📦 <b>Modullar ro'yxati:</b>",
        reply_markup=modules_list_keyboard(modules),
    )


# ── Module detail ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^admin:module:\d+$"))
async def module_detail(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[2])
    repo = ModuleRepository(session)
    module = await repo.get_by_id(module_id)
    if not module:
        await callback.answer("Modul topilmadi.", show_alert=True)
        return

    from bot.db.repositories import QuestionRepository
    q_repo = QuestionRepository(session)
    count = await q_repo.count_by_module(module_id)

    status = "✅ Faol" if module.is_active else "❌ Nofaol"
    await callback.message.edit_text(
        f"📦 <b>{module.name}</b>\n\n"
        f"📄 Tavsif: {module.description or '—'}\n"
        f"🔢 Tartib: {module.order}\n"
        f"📊 Savollar: {count}\n"
        f"🔘 Status: {status}",
        reply_markup=module_detail_keyboard(module),
    )


# ── Create module ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:module:create")
async def create_module_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminModuleStates.waiting_name)
    await callback.message.edit_text(
        "📦 <b>Yangi modul yaratish</b>\n\nModul nomini kiriting:",
        reply_markup=cancel_keyboard("admin:modules"),
    )


@router.message(AdminModuleStates.waiting_name)
async def create_module_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminModuleStates.waiting_description)
    await message.answer(
        "📄 Modul tavsifini kiriting (yoki /skip yozing):",
        reply_markup=cancel_keyboard("admin:modules"),
    )


@router.message(AdminModuleStates.waiting_description)
async def create_module_desc(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    desc = None if message.text.strip() == "/skip" else message.text.strip()
    data = await state.get_data()
    repo = ModuleRepository(session)
    module = await repo.create(name=data["name"], description=desc)
    await state.clear()
    await message.answer(
        f"✅ Modul yaratildi!\n\n<b>{module.name}</b>\nID: {module.id}",
        reply_markup=module_detail_keyboard(module),
    )


# ── Toggle active ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:module:toggle:"))
async def toggle_module(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[3])
    repo = ModuleRepository(session)
    module = await repo.get_by_id(module_id)
    if not module:
        await callback.answer("Modul topilmadi.", show_alert=True)
        return
    await repo.update(module, is_active=not module.is_active)
    status = "yoqildi ✅" if module.is_active else "o'chirildi ❌"
    await callback.answer(f"Modul {status}")

    from bot.db.repositories import QuestionRepository
    q_repo = QuestionRepository(session)
    count = await q_repo.count_by_module(module_id)
    status_txt = "✅ Faol" if module.is_active else "❌ Nofaol"
    await callback.message.edit_text(
        f"📦 <b>{module.name}</b>\n\n"
        f"📄 Tavsif: {module.description or '—'}\n"
        f"🔢 Tartib: {module.order}\n"
        f"📊 Savollar: {count}\n"
        f"🔘 Status: {status_txt}",
        reply_markup=module_detail_keyboard(module),
    )


# ── Edit name ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:module:edit_name:"))
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[3])
    await state.set_state(AdminModuleStates.editing_name)
    await state.update_data(module_id=module_id)
    await callback.message.edit_text(
        "✏️ Yangi nomni kiriting:",
        reply_markup=cancel_keyboard(f"admin:module:{module_id}"),
    )


@router.message(AdminModuleStates.editing_name)
async def edit_name_finish(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    repo = ModuleRepository(session)
    module = await repo.get_by_id(data["module_id"])
    if module:
        await repo.update(module, name=message.text.strip())
    await state.clear()
    await message.answer(f"✅ Nom o'zgartirildi: <b>{message.text.strip()}</b>")


# ── Edit description ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:module:edit_desc:"))
async def edit_desc_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[3])
    await state.set_state(AdminModuleStates.editing_description)
    await state.update_data(module_id=module_id)
    await callback.message.edit_text(
        "📄 Yangi tavsifni kiriting:",
        reply_markup=cancel_keyboard(f"admin:module:{module_id}"),
    )


@router.message(AdminModuleStates.editing_description)
async def edit_desc_finish(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    repo = ModuleRepository(session)
    module = await repo.get_by_id(data["module_id"])
    if module:
        await repo.update(module, description=message.text.strip())
    await state.clear()
    await message.answer("✅ Tavsif o'zgartirildi.")


# ── Edit order ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:module:edit_order:"))
async def edit_order_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[3])
    await state.set_state(AdminModuleStates.editing_order)
    await state.update_data(module_id=module_id)
    await callback.message.edit_text(
        "🔢 Yangi tartib raqamini kiriting (masalan: 1, 2, 3):",
        reply_markup=cancel_keyboard(f"admin:module:{module_id}"),
    )


@router.message(AdminModuleStates.editing_order)
async def edit_order_finish(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    try:
        order = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Iltimos, son kiriting.")
        return
    data = await state.get_data()
    repo = ModuleRepository(session)
    module = await repo.get_by_id(data["module_id"])
    if module:
        await repo.update(module, order=order)
    await state.clear()
    await message.answer(f"✅ Tartib o'zgartirildi: <b>{order}</b>")


# ── Delete module ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:module:delete:"))
async def delete_module_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[3])
    await callback.message.edit_text(
        "⚠️ Haqiqatan ham bu modulni o'chirmoqchimisiz?\n<b>Barcha savollar ham o'chib ketadi!</b>",
        reply_markup=confirm_delete_keyboard("module", module_id),
    )


@router.callback_query(F.data.startswith("admin:confirm_delete:module:"))
async def delete_module_execute(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    module_id = int(callback.data.split(":")[3])
    repo = ModuleRepository(session)
    module = await repo.get_by_id(module_id)
    if module:
        await repo.delete(module)
    await callback.answer("✅ Modul o'chirildi.")
    modules = await repo.get_all()
    await callback.message.edit_text(
        "📦 <b>Modullar ro'yxati:</b>",
        reply_markup=modules_list_keyboard(modules),
    )
