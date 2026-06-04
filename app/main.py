from fastapi import FastAPI
from schemas import (
    PredictRequest,
    PredictResponse,
    BatchPredictRequest,
    BatchPredictResponse,
)
from engine import QueuePredictor

app = FastAPI(title="FastQueue Service")
engine = QueuePredictor(model_path="path/to/model.pkl")


@app.post("/api/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Эндпоинт для предсказания времени защиты одного студента.
    """

    duration = engine.predict_once(request)

    # TODO: Реализовать логику предсказания на основе входных данных
    return {
        "predicted_duration_minutes": duration,
        "estimated_waiting_time_minutes": 30.0,
        "is_fallback": True,
        "model_version": "stub_v1",
    }


@app.post("/api/v1/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(request: BatchPredictRequest):
    """
    Эндпоинт для предсказания времени защиты для всех студентов в очереди.
    """

    # TODO: Реализовать логику предсказания для каждого студента в очереди на основе входных данных
    return {
        "predictions": [
            {
                "student_id": item.student_id,
                "predicted_duration": 15.0,
                "estimated_waiting_time": index * 15.0,
            }
            for index, item in enumerate(request.queue)
        ],
        "is_fallback": True,
        "model_version": "stub_v1",
    }


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
