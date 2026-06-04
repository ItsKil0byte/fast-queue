import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import os


def train():
    """
    Обучение модели на основе данных из data/defense_history.csv и
    сохранение обученной модели в app/models/ridge_v1.joblib
    """

    # 1. Загрузка данных
    data = "data/defense_history.csv"
    if not os.path.exists(data):
        print(f"Error: {data} not found.")
        return

    df = pd.read_csv(data)

    # 2. Выделение признаков и целевой переменной
    X = df[["teacher_id", "lab_difficulty", "time_elapsed_minutes"]]
    y = df["duration_minutes"]

    # 3. Определение предобработки для категориальных и числовых признаков
    categorical_features = ["teacher_id"]
    numerical_features = ["lab_difficulty", "time_elapsed_minutes"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", "passthrough", numerical_features),
        ]
    )

    # 4. Создание пайплайна с предобработкой и регрессором
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", Ridge(alpha=1.0)),
        ]
    )

    # 5. Разделение данных на обучающую и тестовую выборки
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 6. Тренировка модели
    model.fit(X_train, y_train)

    # 7. Оценка модели на тестовой выборке
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    mape = mean_absolute_percentage_error(y_test, y_pred)

    print("Обучение завершено.")
    print(f"MAE: {mae:.2f} минут (Цель < 3.0)")
    print(f"MAPE: {mape:.2%} (Цель < 20%)")

    # 8. Сохранение модели
    model_dir = "app/models"
    os.makedirs(model_dir, exist_ok=True)

    model_path = os.path.join(model_dir, "ridge_v1.joblib")
    joblib.dump(model, model_path)

    print(f"Модель сохранена в {model_path}")


if __name__ == "__main__":
    train()
