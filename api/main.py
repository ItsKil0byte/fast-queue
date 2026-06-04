from fastapi import FastAPI
from contextlib import asynccontextmanager
import os

from api.schemas import (
    CreateQueueRequest,
    FinishDefenseRequest,
    JoinQueueRequest,
    PredictRequest,
    PredictResponse,
    BatchPredictRequest,
    BatchPredictResponse,
)
from api.database import DatabaseManager
from api.engine import QueuePredictor

# Глобальные объекты для работы с БД и предикциями
database = DatabaseManager()
engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Логика, выполняющаяся при старте и завершении приложения.
    """
    global engine

    # Инициализация базы данных
    await database.init_db()

    # Инициализация движка предсказаний
    model_path = "api/models/ridge_v1.joblib"
    if not os.path.exists(model_path):
        print(
            f"Модель не найдена по пути {model_path}. Будет использоваться резервная логика."
        )
        model_path = None

    try:
        engine = QueuePredictor(model_path=model_path)
        if model_path:
            print(f"Модель успешно загружена из {model_path}")
    except Exception as e:
        print(f"Ошибка при загрузке модели: {e}")
        engine = QueuePredictor(model_path=None)

    yield


app = FastAPI(title="FastQueue Service", lifespan=lifespan)


@app.post("/api/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Эндпоинт для предсказания времени защиты для одного студента.
    """

    duration = engine.predict_duration(
        teacher_id=request.teacher_id,
        lab_difficulty=request.lab_difficulty,
        time_elapsed=request.time_elapsed_minutes,
    )

    # Расчет времени ожидания (упрощенно для одиночного эндпоинта)
    estimated_waiting = duration * (request.queue_position - 1)

    return {
        "predicted_duration_minutes": duration,
        "estimated_waiting_time_minutes": estimated_waiting,
        "is_fallback": engine.model is None,
        "model_version": "ridge_v1" if engine.model else "fallback_v1",
    }


@app.post("/api/v1/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(request: BatchPredictRequest):
    """
    Эндпоинт для пакетного предсказания времени защиты для всего списка студентов.
    """

    predictions = engine.predict_batch(
        teacher_id=request.teacher_id,
        time_elapsed=request.time_elapsed_minutes,
        queue=request.queue,
    )

    return {
        "predictions": predictions,
        "is_fallback": engine.model is None,
        "model_version": "ridge_v1" if engine.model else "fallback_v1",
    }


@app.post("/api/v1/queue/create")
async def create_queue(request: CreateQueueRequest):
    """
    Эндпоинт для создания новой очереди.

    :param request: Данные для создания очереди
    :return: ID созданной очереди и статус "active"
    """

    queue_id = await database.create_queue(
        teacher_id=request.teacher_id,
        subject_name=request.subject_name,
        classroom=request.classroom,
    )

    return {"queue_id": queue_id, "status": "active"}


@app.post("/api/v1/queue/add")
async def join_queue(request: JoinQueueRequest):
    """
    Эндпоинт для добавления студента в очередь.

    :param request: Данные для добавления студента в очередь
    :return: Позиция студента в очереди и статус "waiting"
    """

    position = await database.add_student_to_queue(
        queue_id=request.queue_id,
        student_id=request.student_id,
        lab_id=request.lab_id,
        lab_difficulty=request.lab_difficulty,
    )

    return {"position": position, "status": "waiting"}


@app.post("/api/v1/queue/next")
async def call_next(queue_id: int):
    """
    Эндпоинт для вызова следующего студента из очереди.

    :param queue_id: ID очереди
    :return: Данные вызванного студента или сообщение о том, что очередь пуста
    """

    student = await database.call_next_student(queue_id)

    if not student:
        return {"message": "Очередь пуста", "student": None}

    return {"message": "Студент вызван", "student": student}


@app.post("/api/v1/queue/finish-student")
async def finish_student(request: FinishDefenseRequest):
    """
    Эндпоинт для завершения защиты студента и сохранения данных для обучения ИИ.

    :param request: Данные для завершения защиты студента
    :return: Сообщение о том, что защита завершена и данные сохранены
    """

    await database.finish_defense(request.record_id, request.score)

    return {"message": "Защита завершена, данные сохранены для обучения ИИ"}


@app.post("/api/v1/queue/close")
async def close_queue(queue_id: int):
    """
    Эндпоинт для закрытия очереди.

    :param queue_id: ID очереди
    :return: Сообщение о том, что очередь закрыта
    """

    await database.close_queue(queue_id)

    return {"message": "Очередь закрыта"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
