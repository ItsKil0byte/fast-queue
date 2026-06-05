from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
 
 
def teacher_idle_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🚀 Открыть новую очередь")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
 
 
def teacher_managing_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="➡️ Следующий студент")
    builder.button(text="📊 Статус очереди")
    builder.button(text="✅ Завершить защиту")
    builder.button(text="🔚 Закрыть очередь")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
 
 
def confirm_close_queue_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, закрыть", callback_data="close_queue:yes")
    builder.button(text="❌ Отмена", callback_data="close_queue:no")
    builder.adjust(2)
    return builder.as_markup()
 
 
def finish_score_kb(student_id: int) -> InlineKeyboardMarkup:
    """Выбор оценки при завершении защиты."""
    builder = InlineKeyboardBuilder()
    for score in [3, 4, 5]:
        builder.button(
            text=f"{'⭐' * score} ({score})",
            callback_data=f"score:{student_id}:{score}",
        )
    builder.button(text="⏭ Без оценки", callback_data=f"score:{student_id}:0")
    builder.adjust(3, 1)
    return builder.as_markup()