import joblib
from schemas import PredictRequest


class QueuePredictor:
    def __init__(self, model_path: str):
        try:
            self.model = joblib.load(model_path) if model_path else None
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            self.model = None

    def predict_once(self, request: PredictRequest) -> dict:
        """
        Предсказание времени защиты для одного студента на основе входных данных.
        """

        if self.model:
            # TODO: Реализовать реальную логику предсказания на основе модели и входных данных
            pass

        medians = {1: 10.0, 2: 20.0, 3: 30.0}
        return medians.get(request.lab_difficulty, 15.0)
