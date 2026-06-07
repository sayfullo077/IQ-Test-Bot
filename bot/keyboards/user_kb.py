from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models.module import Module

OPTIONS_LETTERS = ["A", "B", "C", "D", "E", "F"]


def modules_keyboard(modules: list[Module]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in modules:
        builder.button(text=m.name, callback_data=f"start_module:{m.id}")
    builder.adjust(1)
    return builder.as_markup()


def answer_keyboard(options_count: int, question_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for letter in OPTIONS_LETTERS[:options_count]:
        builder.button(
            text=letter,
            callback_data=f"answer:{question_id}:{letter}",
        )
    builder.adjust(options_count)
    return builder.as_markup()


def confirm_start_keyboard(module_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Boshlash", callback_data=f"confirm_start:{module_id}")
    builder.button(text="❌ Bekor qilish", callback_data="cancel_test")
    builder.adjust(2)
    return builder.as_markup()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 IQ Testni boshlash", callback_data="open_modules")
    builder.button(text="📊 Mening natijalarim", callback_data="my_results")
    builder.adjust(1)
    return builder.as_markup()
