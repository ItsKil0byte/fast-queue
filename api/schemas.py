from pydantic import BaseModel, Field
from typing import List, Optional


# --- Models for API Requests and Responses ---


class FinishDefenseRequest(BaseModel):
    record_id: int = Field(..., description="ID записи в очереди")
    score: Optional[int] = Field(None, ge=1, le=5, description="Оценка (необязательно)")


class CreateQueueRequest(BaseModel):
    teacher_id: int = Field(..., description="Уникальный ID преподавателя")
    subject_name: str = Field(..., description="Название предмета")
    classroom: str = Field(..., description="Аудитория проведения защиты")


class JoinQueueRequest(BaseModel):
    queue_id: int = Field(..., description="ID очереди")
    student_id: int = Field(..., description="Уникальный ID студента")
    lab_id: int = Field(..., description="ID лабораторной работы")
    lab_difficulty: int = Field(
        ..., ge=1, le=3, description="Уровень сложности лабораторной работы (1-3)"
    )


# --- Single Prediction Models ---


class PredictRequest(BaseModel):
    teacher_id: int = Field(..., description="Уникальный ID преподавателя")
    lab_difficulty: int = Field(
        ..., ge=1, le=3, description="Уровень сложности лабораторной работы (1-3)"
    )
    queue_position: int = Field(..., ge=1, description="Позиция в очереди")
    time_elapsed_minutes: float = Field(
        ..., ge=0, description="Минуты, прошедшие с начала сессии"
    )
    student_id: int = Field(..., description="Уникальный ID студента")


class PredictResponse(BaseModel):
    predicted_duration_minutes: float = Field(
        ..., description="Предсказанное время для защиты студента в минутах"
    )
    estimated_waiting_time_minutes: float = Field(
        ..., description="Оценочное общее время ожидания для студента в минутах"
    )
    is_fallback: bool = Field(
        ..., description="Использовалась ли резервная модель/логика"
    )
    model_version: str = Field(..., description="Версия используемой ML модели")


# --- Batch Prediction Models ---


class QueueItem(BaseModel):
    student_id: int = Field(..., description="Уникальный ID студента")
    lab_difficulty: int = Field(
        ..., ge=1, le=3, description="Уровень сложности лабораторной работы (1-3)"
    )
    queue_position: int = Field(..., ge=1, description="Позиция в очереди")


class BatchPredictRequest(BaseModel):
    teacher_id: int = Field(..., description="Уникальный ID преподавателя")
    time_elapsed_minutes: float = Field(
        ..., ge=0, description="Минуты, прошедшие с начала сессии"
    )
    queue: List[QueueItem] = Field(
        ..., description="Список студентов, находящихся в очереди"
    )


class PredictionItem(BaseModel):
    student_id: int = Field(..., description="Уникальный ID студента")
    predicted_duration: float = Field(
        ..., description="Предсказанное время для защиты студента в минутах"
    )
    estimated_waiting_time: float = Field(
        ..., description="Оценочное общее время ожидания для студента в минутах"
    )


class BatchPredictResponse(BaseModel):
    predictions: List[PredictionItem] = Field(
        ..., description="Список предсказаний для всех студентов в очереди"
    )
    is_fallback: bool = Field(
        ..., description="Использовалась ли резервная модель/логика"
    )
    model_version: str = Field(..., description="Версия используемой ML модели")
