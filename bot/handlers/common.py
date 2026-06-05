import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from services.api_client import FastQueueAPI, APIError
from keyboards.student_kb import role_selection_kb, student_idle_kb
from keyboards.teacher_kb import teacher_idle_kb
from states.states import StudentSG, TeacherSG

logger = logging.getLogger(__name__)
router = Router()

WELCOME_TEXT = (
    "👋 Привет! Я <b>FastQueue</b> — бот для умных очередей на защиту лабораторных.\n\n"
    "Кто ты?"
)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    api_url: str,
):
    api = FastQueueAPI(api_url)

    try:
        user = await api.get_user(message.from_user.id)

    except APIError as e:
        # Пользователь ещё не зарегистрирован
        if e.status == 404:
            await state.clear()

            await message.answer(
                WELCOME_TEXT,
                reply_markup=role_selection_kb(),
            )
            return

        await message.answer(f"❌ Ошибка: {e.detail}")
        return

    finally:
        await api.close()

    role = user["role"]

    if role == "student":
        await state.set_state(StudentSG.idle)

        await state.update_data(
            student_id=user["telegram_id"],
            student_name=user["full_name"],
        )

        await message.answer(
            f"🎓 С возвращением, <b>{user['full_name']}</b>!",
            reply_markup=student_idle_kb(),
        )

    elif role == "teacher":
        await state.set_state(TeacherSG.idle)

        await state.update_data(
            teacher_id=user["telegram_id"],
            teacher_name=user["full_name"],
        )

        await message.answer(
            f"👨‍🏫 С возвращением, <b>{user['full_name']}</b>!",
            reply_markup=teacher_idle_kb(),
        )

    else:
        await state.clear()

        await message.answer(
            WELCOME_TEXT,
            reply_markup=role_selection_kb(),
        )


@router.callback_query(F.data == "role:student")
async def choose_student(
    callback: CallbackQuery,
    state: FSMContext,
    api_url: str,
):
    user = callback.from_user

    api = FastQueueAPI(api_url)

    try:
        await api.register_user(
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            role="student",
        )

    except APIError as e:
        await callback.answer(
            f"Ошибка: {e.detail}",
            show_alert=True,
        )
        return

    finally:
        await api.close()

    await state.set_state(StudentSG.idle)

    await state.update_data(
        student_id=user.id,
        student_name=user.full_name or user.username or str(user.id),
    )

    await callback.message.edit_text(
        f"🎓 Отлично, <b>{user.first_name}</b>! Ты в режиме студента.\n\n"
        "Нажми кнопку ниже, чтобы записаться в очередь.",
    )

    await callback.message.answer(
        "Главное меню:",
        reply_markup=student_idle_kb(),
    )

    await callback.answer()


@router.callback_query(F.data == "role:teacher")
async def choose_teacher(
    callback: CallbackQuery,
    state: FSMContext,
    api_url: str,
):
    user = callback.from_user

    api = FastQueueAPI(api_url)

    try:
        await api.register_user(
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            role="teacher",
        )

    except APIError as e:
        await callback.answer(
            f"Ошибка: {e.detail}",
            show_alert=True,
        )
        return

    finally:
        await api.close()

    await state.set_state(TeacherSG.idle)

    await state.update_data(
        teacher_id=user.id,
        teacher_name=user.full_name or user.username or str(user.id),
    )

    await callback.message.edit_text(
        f"👨‍🏫 Отлично, <b>{user.first_name}</b>! Ты в режиме преподавателя.",
    )

    await callback.message.answer(
        "Панель преподавателя:",
        reply_markup=teacher_idle_kb(),
    )

    await callback.answer()