from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models.module import Module
from bot.db.models.question import Question


def admin_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Modullar", callback_data="admin:modules")
    builder.button(text="📊 Statistika", callback_data="admin:stats")
    builder.adjust(1)
    return builder.as_markup()


def modules_list_keyboard(modules: list[Module]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in modules:
        status = "✅" if m.is_active else "❌"
        builder.button(text=f"{status} {m.name}", callback_data=f"admin:module:{m.id}")
    builder.button(text="➕ Yangi modul", callback_data="admin:module:create")
    builder.button(text="🔙 Orqaga", callback_data="admin:main")
    builder.adjust(1)
    return builder.as_markup()


def module_detail_keyboard(module: Module) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Savollar", callback_data=f"admin:questions:{module.id}")
    toggle_text = "🔴 O'chirish" if module.is_active else "🟢 Yoqish"
    builder.button(text=toggle_text, callback_data=f"admin:module:toggle:{module.id}")
    builder.button(text="✏️ Nomini o'zgartirish", callback_data=f"admin:module:edit_name:{module.id}")
    builder.button(text="📄 Tavsifini o'zgartirish", callback_data=f"admin:module:edit_desc:{module.id}")
    builder.button(text="🔢 Tartibini o'zgartirish", callback_data=f"admin:module:edit_order:{module.id}")
    builder.button(text="🗑 O'chirish", callback_data=f"admin:module:delete:{module.id}")
    builder.button(text="🔙 Orqaga", callback_data="admin:modules")
    builder.adjust(1)
    return builder.as_markup()


def questions_list_keyboard(module_id: int, questions: list[Question]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for q in questions:
        builder.button(
            text=f"#{q.order} — {q.q_type or 'Savol'} ({q.difficulty or '?'})",
            callback_data=f"admin:question:{q.id}",
        )
    builder.button(text="➕ Yangi savol", callback_data=f"admin:question:create:{module_id}")
    builder.button(text="🔙 Orqaga", callback_data=f"admin:module:{module_id}")
    builder.adjust(1)
    return builder.as_markup()


def question_detail_keyboard(question: Question) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🖼 Rasmni o'zgartirish", callback_data=f"admin:question:edit_image:{question.id}")
    builder.button(text="✅ To'g'ri javobni o'zgartirish", callback_data=f"admin:question:edit_answer:{question.id}")
    builder.button(text="🔢 Variantlar sonini o'zgartirish", callback_data=f"admin:question:edit_options:{question.id}")
    builder.button(text="🗑 O'chirish", callback_data=f"admin:question:delete:{question.id}")
    builder.button(text="🔙 Orqaga", callback_data=f"admin:questions:{question.module_id}")
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete_keyboard(entity: str, entity_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data=f"admin:confirm_delete:{entity}:{entity_id}")
    builder.button(text="❌ Bekor qilish", callback_data=f"admin:{entity}:{entity_id}" if entity == "question" else f"admin:module:{entity_id}")
    builder.adjust(2)
    return builder.as_markup()


def cancel_keyboard(back_callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data=back_callback)
    return builder.as_markup()
