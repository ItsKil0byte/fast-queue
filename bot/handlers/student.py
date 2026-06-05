import logging
 
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
 
from keyboards.student_kb import (
    lab_number_kb,
    lab_difficulty_kb,
    student_in_queue_kb,
    student_idle_kb,
    confirm_leave_kb,
)
from services.api_client import FastQueueAPI, APIError
from states.states import StudentSG
 
logger = logging.getLogger(__name__)
router = Router()
 
DIFFICULTY_LABEL = {1: "🟢 Лёгкая", 2: "🟡 Средняя", 3: "🔴 Сложная"}
 
 
def _fmt_minutes(minutes: float) -> str:
    m = int(round(minutes))
    if m <= 0:
        return "сейчас"
    return f"≈ {m} мин."
 
 
# ── Запись в очередь ──────────────────────────────────────────────────────────
 
@router.message(StudentSG.idle, F.text == "📋 Записаться в очередь")
async def start_enrollment(message: Message, state: FSMContext):
    data = await state.get_data()
    # Если queue_id уже задан извне (преподаватель сказал ID) — можно использовать
    # Пока просим студента ввести ID очереди вручную
    await state.set_state(StudentSG.entering_queue_id)
    await message.answer(
        "🔢 Введи <b>ID очереди</b>, который сообщил преподаватель\n"
        "(например: <code>1</code>):"
    )
 
 
@router.message(StudentSG.entering_queue_id)
async def enter_queue_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Введи числовой ID очереди:")
        return
    queue_id = int(text)
    await state.update_data(queue_id=queue_id)
    await state.set_state(StudentSG.choosing_lab)
    await message.answer(
        f"✅ Очередь <code>{queue_id}</code>\n\n"
        "📚 Выбери номер лабораторной работы:",
        reply_markup=lab_number_kb(),
    )
 
 
@router.callback_query(StudentSG.choosing_lab, F.data.startswith("lab_num:"))
async def choose_lab_number(callback: CallbackQuery, state: FSMContext):
    lab_id = int(callback.data.split(":")[1])
    await state.update_data(lab_id=lab_id)
    await callback.message.edit_text(
        f"🔢 Лабораторная <b>№{lab_id}</b>.\n\nОцени сложность:",
        reply_markup=lab_difficulty_kb(lab_id),
    )
    await callback.answer()
 
 
@router.callback_query(StudentSG.choosing_lab, F.data.startswith("lab_diff:"))
async def choose_lab_difficulty(callback: CallbackQuery, state: FSMContext, api_url: str):
    _, lab_id_str, diff_str = callback.data.split(":")
    lab_id = int(lab_id_str)
    lab_difficulty = int(diff_str)
 
    data = await state.get_data()
    student_id: int = data["student_id"]
    queue_id: int = data["queue_id"]
 
    api = FastQueueAPI(api_url)
    try:
        result = await api.add_to_queue(
            queue_id=queue_id,
            student_id=student_id,
            lab_id=lab_id,
            lab_difficulty=lab_difficulty,
        )
    except APIError as e:
        await callback.message.edit_text(
            f"❌ Ошибка при записи: {e.detail}\n\n"
            "Проверь ID очереди и попробуй снова."
        )
        await state.set_state(StudentSG.idle)
        await callback.message.answer("Главное меню:", reply_markup=student_idle_kb())
        await callback.answer()
        return
    finally:
        await api.close()
 
    position: int = result.get("position", "?")
 
    await state.update_data(lab_id=lab_id, lab_difficulty=lab_difficulty)
    await state.set_state(StudentSG.in_queue)
 
    diff_label = DIFFICULTY_LABEL.get(lab_difficulty, str(lab_difficulty))
    await callback.message.edit_text(
        f"✅ <b>Ты записан в очередь!</b>\n\n"
        f"🔢 Лаба №{lab_id} ({diff_label})\n"
        f"📍 Позиция: <b>{position}</b>\n\n"
        "Я уведомлю тебя, когда подойдёт твоя очередь 🔔"
    )
    await callback.message.answer(
        "Управление очередью:", reply_markup=student_in_queue_kb()
    )
    await callback.answer()
 
 
# ── Проверка позиции ──────────────────────────────────────────────────────────
 
@router.message(StudentSG.in_queue, F.text == "⏱ Моя позиция и время")
async def check_position(message: Message, state: FSMContext, api_url: str):
    data = await state.get_data()
    queue_id: int = data.get("queue_id")
    student_id: int = data.get("student_id")
    teacher_id: int = data.get("teacher_id_of_queue", 0)
    lab_difficulty: int = data.get("lab_difficulty", 2)
 
    if not queue_id:
        await message.answer("⚠️ Нет данных об очереди. Запишись снова.")
        return
 
    # Получаем список очереди из БД через predict/batch
    # Для этого нам нужны данные об очереди — делаем простой predict для себя
    api = FastQueueAPI(api_url)
    try:
        result = await api.predict_batch(
            teacher_id=teacher_id,
            time_elapsed_minutes=0.0,
            queue=[{
                "student_id": student_id,
                "lab_difficulty": lab_difficulty,
                "queue_position": 1,
            }],
        )
        predictions = result.get("predictions", [])
        if predictions:
            wait = predictions[0].get("estimated_waiting_time", 0.0)
            duration = predictions[0].get("predicted_duration", 0.0)
            await message.answer(
                f"⏱ Примерное время до твоей защиты: <b>{_fmt_minutes(wait)}</b>\n"
                f"📖 Ожидаемая длительность защиты: <b>{_fmt_minutes(duration)}</b>"
            )
        else:
            await message.answer("⚠️ Не удалось получить прогноз.")
    except APIError as e:
        await message.answer(f"❌ Ошибка: {e.detail}")
    finally:
        await api.close()
 
 
# ── Выход из очереди ──────────────────────────────────────────────────────────
 
@router.message(StudentSG.in_queue, F.text == "🚪 Выйти из очереди")
async def ask_leave_queue(message: Message):
    await message.answer(
        "Ты уверен, что хочешь выйти из очереди?\n\n"
        "⚠️ Выход из очереди сейчас не поддерживается API — "
        "сообщи преподавателю, что хочешь пропустить свою очередь.",
        reply_markup=confirm_leave_kb(),
    )
 
 
@router.callback_query(StudentSG.in_queue, F.data == "confirm_leave:yes")
async def confirm_leave(callback: CallbackQuery, state: FSMContext):
    # API не имеет эндпоинта leave — просто сбрасываем стейт на стороне бота
    await state.set_state(StudentSG.idle)
    await callback.message.edit_text(
        "👋 Ты вышел из очереди на стороне бота.\n"
        "Не забудь предупредить преподавателя!"
    )
    await callback.message.answer("Главное меню:", reply_markup=student_idle_kb())
    await callback.answer()
 
 
@router.callback_query(StudentSG.in_queue, F.data == "confirm_leave:no")
async def cancel_leave(callback: CallbackQuery):
    await callback.message.edit_text("Хорошо, остаёшься в очереди 👍")
    await callback.answer()
 
 
# ── Студент вызван ────────────────────────────────────────────────────────────
 
@router.message(StudentSG.at_defense)
async def at_defense_message(message: Message):
    await message.answer(
        "🎤 Ты сейчас на защите! Удачи!\n\n"
        "Когда закончишь, преподаватель завершит сдачу со своей стороны."
    )
 