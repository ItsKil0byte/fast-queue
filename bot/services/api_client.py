"""
Клиент для общения с FastAPI ML-сервисом.
Все методы соответствуют реальным эндпоинтам API.
"""
import logging
from typing import Any
 
import aiohttp
 
logger = logging.getLogger(__name__)
 
 
class APIError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"API error {status}: {detail}")
 
 
class FastQueueAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None
 
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session
 
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
 
    async def _post(self, path: str, payload: dict) -> dict:
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    raise APIError(resp.status, data.get("detail", str(data)))
                return data
        except aiohttp.ClientError as e:
            raise APIError(0, f"Нет связи с сервисом: {e}") from e
 
    async def _post_params(self, path: str, params: dict) -> dict:
        """POST с query-параметрами (не JSON body)."""
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.post(url, params=params) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    raise APIError(resp.status, data.get("detail", str(data)))
                return data
        except aiohttp.ClientError as e:
            raise APIError(0, f"Нет связи с сервисом: {e}") from e
 
    # ── Очередь ──────────────────────────────────────────────────────────────
 
    async def create_queue(
        self,
        teacher_id: int,
        subject_name: str,
        classroom: str,
    ) -> dict:
        """POST /api/v1/queue/create — создать очередь."""
        return await self._post(
            "/api/v1/queue/create",
            {
                "teacher_id": teacher_id,
                "subject_name": subject_name,
                "classroom": classroom,
            },
        )
 
    async def add_to_queue(
        self,
        queue_id: int,
        student_id: int,
        lab_id: int,
        lab_difficulty: int,
    ) -> dict:
        """POST /api/v1/queue/add — записать студента в очередь.
        Возвращает {"position": int, "status": "waiting"}
        """
        return await self._post(
            "/api/v1/queue/add",
            {
                "queue_id": queue_id,
                "student_id": student_id,
                "lab_id": lab_id,
                "lab_difficulty": lab_difficulty,
            },
        )
 
    async def next_student(self, queue_id: int) -> dict:
        """POST /api/v1/queue/next?queue_id=... — вызвать следующего.
        Возвращает {"message": ..., "student": {"record_id", "student_id", "position"} | None}
        """
        return await self._post_params(
            "/api/v1/queue/next",
            {"queue_id": queue_id},
        )
 
    async def finish_student(
        self,
        record_id: int,
        score: int | None = None,
    ) -> dict:
        """POST /api/v1/queue/finish-student — завершить защиту.
        Принимает record_id (не student_id!), score опционален.
        """
        payload: dict[str, Any] = {"record_id": record_id}
        if score is not None:
            payload["score"] = score
        return await self._post("/api/v1/queue/finish-student", payload)
 
    async def close_queue(self, queue_id: int) -> dict:
        """POST /api/v1/queue/close?queue_id=... — закрыть очередь."""
        return await self._post_params(
            "/api/v1/queue/close",
            {"queue_id": queue_id},
        )
 
    async def get_active_queue_students(self, queue_id: int) -> list:
        """GET /api/v1/queue/{queue_id}/students — список студентов в очереди.
        Использует database.get_active_queue напрямую через эндпоинт если добавят,
        пока — батч-предикт как источник данных об очереди.
        """
        # Этого эндпоинта нет в API — используем predict/batch чтобы получить
        # данные и время ожидания одновременно (см. get_queue_with_predictions)
        raise NotImplementedError
 
    async def predict_batch(
        self,
        teacher_id: int,
        time_elapsed_minutes: float,
        queue: list[dict],
    ) -> dict:
        """POST /api/v1/predict/batch — пакетный расчёт времени."""
        return await self._post(
            "/api/v1/predict/batch",
            {
                "teacher_id": teacher_id,
                "time_elapsed_minutes": time_elapsed_minutes,
                "queue": queue,
            },
        )