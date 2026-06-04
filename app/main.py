from fastapi import FastAPI
from contextlib import asynccontextmanager
from schemas import (
    PredictRequest,
    PredictResponse,
    BatchPredictRequest,
    BatchPredictResponse,
)
from database import DatabaseManager
import joblib
import os

# Плейсхолдер для модели, будет загружаться при старте приложения
model = None
database = DatabaseManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Логика, выполняющаяся при старте и завершении приложения.
    Здесь мы инициализируем базу данных и загружаем ML модель.
    """

    # Инициализация базы данных и загрузка модели при старте приложения

    global model
    await database.init_db()

    model_path = "app/models/ridge_v1.joblib"

    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            print(f"Model loaded successfully from {model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
    else:
        print(f"Warning: Model file {model_path} not found. Running in fallback mode.")

    yield
    # Здесь можно добавить код для очистки ресурсов при завершении приложения, если это необходимо


app = FastAPI(title="FastQueue Service", lifespan=lifespan)


@app.post("/api/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Эндпоинт для предсказания времени защиты для одного студента.
    """

    is_fallback = True
    model_version = "fallback_v1"

    # Резервная логика для предсказания времени защиты, если модель не загружена
    predicted_duration = {1: 8.0, 2: 12.0, 3: 20.0}.get(request.lab_difficulty, 12.0)

    if model:
        try:
            import pandas as pd

            # Формируем DataFrame для предсказания, используя только необходимые признаки
            features = pd.DataFrame(
                [
                    {
                        "teacher_id": request.teacher_id,
                        "lab_difficulty": request.lab_difficulty,
                        "time_elapsed_minutes": request.time_elapsed_minutes,
                    }
                ]
            )
            predicted_duration = float(model.predict(features)[0])
            is_fallback = False
            model_version = "ridge_v1"
        except Exception as e:
            print(f"Prediction error: {e}")

    # Оценочное время ожидания для студента на основе его позиции в очереди и предсказанных времен других студентов
    estimated_waiting = predicted_duration * (request.queue_position - 1)

    return {
        "predicted_duration_minutes": predicted_duration,
        "estimated_waiting_time_minutes": estimated_waiting,
        "is_fallback": is_fallback,
        "model_version": model_version,
    }


@app.post("/api/v1/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(request: BatchPredictRequest):
    """
    Эндпоинт для пакетного предсказания времени защиты для всего списка студентов.
    """

    predictions = []
    current_waiting_time = 0.0
    is_fallback = model is None
    model_version = "ridge_v1" if model else "fallback_v1"

    for item in request.queue:
        # Резервная логика для предсказания времени защиты, если модель не загружена
        duration = {1: 8.0, 2: 12.0, 3: 20.0}.get(item.lab_difficulty, 12.0)

        if model:
            try:
                import pandas as pd

                features = pd.DataFrame(
                    [
                        {
                            "teacher_id": request.teacher_id,
                            "lab_difficulty": item.lab_difficulty,
                            "time_elapsed_minutes": request.time_elapsed_minutes,
                        }
                    ]
                )
                duration = float(model.predict(features)[0])
            except Exception as e:
                print(f"Batch prediction error: {e}")
                is_fallback = True

        predictions.append(
            {
                "student_id": item.student_id,
                "predicted_duration": duration,
                "estimated_waiting_time": current_waiting_time,
            }
        )

        # Обновляем текущее время ожидания, добавляя предсказанное время текущего студента
        current_waiting_time += duration

    return {
        "predictions": predictions,
        "is_fallback": is_fallback,
        "model_version": model_version,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
