from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
 
 
def role_selection_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎓 Я студент", callback_data="role:student")
    builder.button(text="👨‍🏫 Я преподаватель", callback_data="role:teacher")
    builder.adjust(1)
    return builder.as_markup()
 
 
def student_idle_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Записаться в очередь")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
 
 
def student_in_queue_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="⏱ Моя позиция и время")
    builder.button(text="🚪 Выйти из очереди")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
 
 
def lab_number_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"lab_num:{i}")
    builder.adjust(5)
    return builder.as_markup()
 
 
def lab_difficulty_kb(lab_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="1 — Лёгкая 🟢", callback_data=f"lab_diff:{lab_id}:1")
    builder.button(text="2 — Средняя 🟡", callback_data=f"lab_diff:{lab_id}:2")
    builder.button(text="3 — Сложная 🔴", callback_data=f"lab_diff:{lab_id}:3")
    builder.adjust(1)
    return builder.as_markup()
 
 
def confirm_leave_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, выйти", callback_data="confirm_leave:yes")
    builder.button(text="❌ Отмена", callback_data="confirm_leave:no")
    builder.adjust(2)
    return builder.as_markup()
 