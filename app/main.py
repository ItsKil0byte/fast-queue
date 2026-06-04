from fastapi import FastAPI
from contextlib import asynccontextmanager
import os

from schemas import (
    PredictRequest,
    PredictResponse,
    BatchPredictRequest,
    BatchPredictResponse,
)
from database import DatabaseManager
from engine import QueuePredictor

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
    model_path = "app/models/ridge_v1.joblib"
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
