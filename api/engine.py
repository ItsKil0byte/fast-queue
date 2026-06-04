import pandas as pd
import joblib
from api.schemas import PredictRequest, QueueItem


class QueuePredictor:
    def __init__(self, model_path: str):
        self.model = joblib.load(model_path) if model_path else None
        self.fallback_medians = {1: 8.0, 2: 12.0, 3: 20.0}

    def predict_duration(
        self, teacher_id: int, lab_difficulty: int, time_elapsed: float
    ) -> float:
        """Предсказание времени защиты для одного студента на основе данных о преподавателе, сложности лабораторной работы и времени, прошедшего с начала сессии.
        - Если модель не загружена, возвращает медианное время для данной сложности лабораторной работы из заранее определенного словаря.
        - Если модель загружена, формирует DataFrame с необходимыми признаками и получает предсказание от модели.

        :param teacher_id: Уникальный ID преподавателя
        :param lab_difficulty: Сложность лабораторной работы
        :param time_elapsed: Время, прошедшее с начала сессии (в минутах)
        :return: Предсказанное время защиты (в минутах)
        """

        if not self.model:
            return self.fallback_medians.get(lab_difficulty, 12.0)

        features = pd.DataFrame(
            [
                {
                    "teacher_id": teacher_id,
                    "lab_difficulty": lab_difficulty,
                    "time_elapsed_minutes": time_elapsed,
                }
            ]
        )
        return float(self.model.predict(features)[0])

    def predict_batch(self, teacher_id: int, time_elapsed: float, queue: [QueueItem]):
        """Пакетное предсказание времени защиты для списка студентов в очереди.
        - Принимает список студентов с их данными и возвращает предсказанное время для каждого студента, а также оценочное время ожидания для каждого студента на основе предсказанных времен других студентов в очереди.
        - Если модель не загружена, для предсказания времени защиты используется простая логика, основанная на сложности лабораторной работы.
        - Возвращает список предсказаний для каждого студента, а также информацию о том, использовалась ли резервная логика и какая версия модели была использована для предсказания.

        :param teacher_id: Уникальный ID преподавателя
        :param time_elapsed: Время, прошедшее с начала сессии (в минутах)
        :param queue: Список студентов в очереди с их данными
        :return: Список предсказаний для каждого студента
        """

        predictions = []
        current_waiting_time = 0.0

        for item in queue:
            estimated_time = time_elapsed + current_waiting_time

            duration = self.predict_duration(
                teacher_id, item.lab_difficulty, estimated_time
            )

            predictions.append(
                {
                    "student_id": item.student_id,
                    "predicted_duration": duration,
                    "estimated_waiting_time": current_waiting_time,
                }
            )

            current_waiting_time += duration

        return predictions
