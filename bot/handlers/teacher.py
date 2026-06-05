import logging
 
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
 
from keyboards.teacher_kb import (
    teacher_idle_kb,
    teacher_managing_kb,
    confirm_close_queue_kb,
    finish_score_kb,
)
from services.api_client import FastQueueAPI, APIError
from states.states import TeacherSG
 
logger = logging.getLogger(__name__)
router = Router()
 
 
def _fmt_minutes(minutes: float) -> str:
    m = int(round(minutes))
    return f"≈ {m} мин." if m > 0 else "сейчас"
 
 
# ── Создание очереди ──────────────────────────────────────────────────────────
 
@router.message(TeacherSG.idle, F.text == "🚀 Открыть новую очередь")
async def start_create_queue(message: Message, state: FSMContext):
    await state.set_state(TeacherSG.creating_queue)
    await message.answer(
        "📝 Введи <b>название предмета</b> (например: «Математический анализ»):"
    )
 
 
@router.message(TeacherSG.creating_queue)
async def get_subject_name(message: Message, state: FSMContext):
    subject = message.text.strip()
    if len(subject) < 2:
        await message.answer("⚠️ Слишком короткое название. Попробуй ещё раз:")
        return
    await state.update_data(subject_name=subject)
    await state.set_state(TeacherSG.creating_queue_classroom)
    await message.answer(
        f"✅ Предмет: <b>{subject}</b>\n\n"
        "🏫 Теперь введи <b>номер кабинета</b> (например: «301»):"
    )
 
 
@router.message(TeacherSG.creating_queue_classroom)
async def get_classroom(message: Message, state: FSMContext, api_url: str):
    classroom = message.text.strip()
    if not classroom:
        await message.answer("⚠️ Введи номер кабинета:")
        return
 
    data = await state.get_data()
    teacher_id: int = data["teacher_id"]
    subject_name: str = data["subject_name"]
 
    api = FastQueueAPI(api_url)
    try:
        result = await api.create_queue(
            teacher_id=teacher_id,
            subject_name=subject_name,
            classroom=classroom,
        )
    except APIError as e:
        await message.answer(f"❌ Ошибка создания очереди: {e.detail}")
        return
    finally:
        await api.close()
 
    queue_id: int = result["queue_id"]
    await state.update_data(queue_id=queue_id, classroom=classroom, subject_name=subject_name)
    await state.set_state(TeacherSG.managing)
 
    await message.answer(
        f"🟢 <b>Очередь открыта!</b>\n\n"
        f"📚 Предмет: {subject_name}\n"
        f"🏫 Кабинет: {classroom}\n"
        f"🆔 ID очереди: <code>{queue_id}</code>\n\n"
        "Студенты уже могут записываться через бота.",
        reply_markup=teacher_managing_kb(),
    )
 
 
# ── Следующий студент ─────────────────────────────────────────────────────────
 
@router.message(TeacherSG.managing, F.text == "➡️ Следующий студент")
async def call_next_student(message: Message, state: FSMContext, api_url: str, bot: Bot):
    data = await state.get_data()
    queue_id: int = data.get("queue_id")
 
    api = FastQueueAPI(api_url)
    try:
        result = await api.next_student(queue_id=queue_id)
    except APIError as e:
        await message.answer(f"❌ Ошибка: {e.detail}")
        return
    finally:
        await api.close()
 
    student = result.get("student")
    if not student:
        await message.answer("🏁 Очередь пуста! Больше студентов нет.")
        return
 
    student_id: int = student["student_id"]
    record_id: int = student["record_id"]
    position: int = student["position"]
 
    # Сохраняем record_id — он нужен для finish-student
    await state.update_data(
        current_student_id=student_id,
        current_record_id=record_id,
        current_position=position,
    )
 
    await message.answer(
        f"📢 <b>Вызван студент #{position}</b>\n"
        f"🆔 Telegram ID: <code>{student_id}</code>\n\n"
        "Нажми «✅ Завершить защиту», когда студент сдаст.",
        reply_markup=teacher_managing_kb(),
    )
 
    # Пуш студенту
    try:
        await bot.send_message(
            chat_id=student_id,
            text="🔔 <b>Тебя вызывают!</b>\n\nПодходи к преподавателю — сейчас твоя очередь! Удачи! 🍀",
        )
    except Exception as e:
        logger.warning("Could not notify student %s: %s", student_id, e)
 

@router.message(
    TeacherSG.managing,
    F.text == "📊 Статус очереди",
)
async def queue_status(
    message: Message,
    state: FSMContext,
    api_url: str,
):
    data = await state.get_data()

    queue_id = data.get("queue_id")

    if not queue_id:
        await message.answer("❌ Очередь не найдена")
        return

    api = FastQueueAPI(api_url)

    try:
        result = await api.get_queue(queue_id)

    except APIError as e:
        await message.answer(f"❌ Ошибка: {e.detail}")
        return

    finally:
        await api.close()

    students = result["students"]

    if not students:
        await message.answer("📭 Очередь пуста")
        return

    text = (
        f"📊 <b>Статус очереди</b>\n\n"
        f"👥 Ожидают: {len(students)}\n\n"
    )

    for student in students:
        text += (
            f"#{student['position']} | "
            f"ЛР {student['lab_difficulty']}\n"
        )

    await message.answer(text)
 

# ── Завершить защиту ──────────────────────────────────────────────────────────
 
@router.message(TeacherSG.managing, F.text == "✅ Завершить защиту")
async def finish_defense(message: Message, state: FSMContext):
    data = await state.get_data()
    current_record_id = data.get("current_record_id")
    current_student_id = data.get("current_student_id")
 
    if not current_record_id:
        await message.answer(
            "⚠️ Нет активного студента. Сначала нажми «➡️ Следующий студент»."
        )
        return
 
    await message.answer(
        "Выставь оценку:",
        reply_markup=finish_score_kb(current_record_id),
    )
 
 
@router.callback_query(TeacherSG.managing, F.data.startswith("score:"))
async def handle_score(callback: CallbackQuery, state: FSMContext, api_url: str, bot: Bot):
    _, record_id_str, score_str = callback.data.split(":")
    record_id = int(record_id_str)
    score = int(score_str) if int(score_str) > 0 else None
 
    data = await state.get_data()
    student_id = data.get("current_student_id")
 
    api = FastQueueAPI(api_url)
    try:
        await api.finish_student(record_id=record_id, score=score)
    except APIError as e:
        await callback.message.edit_text(f"❌ Ошибка: {e.detail}")
        await callback.answer()
        return
    finally:
        await api.close()
 
    score_text = f"Оценка: <b>{score}</b> ⭐" if score else "Без оценки"
    await callback.message.edit_text(f"✅ Защита завершена. {score_text}")
    await state.update_data(current_record_id=None, current_student_id=None)
 
    # Уведомляем студента
    if student_id:
        try:
            note = "🏁 Твоя защита завершена!"
            if score:
                note += f" Оценка: <b>{score}</b> ⭐"
            await bot.send_message(chat_id=student_id, text=note)
        except Exception as e:
            logger.warning("Could not notify student %s: %s", student_id, e)
 
    await callback.answer("Готово!")
 
 
# ── Закрытие очереди ──────────────────────────────────────────────────────────
 
@router.message(TeacherSG.managing, F.text == "🔚 Закрыть очередь")
async def ask_close_queue(message: Message):
    await message.answer(
        "⚠️ Закрыть очередь?",
        reply_markup=confirm_close_queue_kb(),
    )
 
 
@router.callback_query(TeacherSG.managing, F.data == "close_queue:yes")
async def confirm_close_queue(callback: CallbackQuery, state: FSMContext, api_url: str):
    data = await state.get_data()
    queue_id: int = data.get("queue_id")
 
    api = FastQueueAPI(api_url)
    try:
        await api.close_queue(queue_id=queue_id)
    except APIError as e:
        await callback.message.edit_text(f"❌ Ошибка: {e.detail}")
        await callback.answer()
        return
    finally:
        await api.close()
 
    await state.set_state(TeacherSG.idle)
    await state.update_data(queue_id=None, current_record_id=None, current_student_id=None)
    await callback.message.edit_text("🔴 Очередь закрыта.")
    from keyboards.teacher_kb import teacher_idle_kb
    await callback.message.answer("Панель преподавателя:", reply_markup=teacher_idle_kb())
    await callback.answer()
 
 
@router.callback_query(TeacherSG.managing, F.data == "close_queue:no")
async def cancel_close_queue(callback: CallbackQuery):
    await callback.message.edit_text("Очередь продолжается 👍")
    await callback.answer()