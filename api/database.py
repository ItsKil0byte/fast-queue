import aiosqlite
import os
from typing import List, Dict, Any, Optional


class DatabaseManager:
    def __init__(self, db_path: str = "data/fastqueue.db"):
        self.db_path = db_path

    async def init_db(self):
        """
        Инициализация базы данных и создание необходимых таблиц.
        """

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    role TEXT CHECK(role IN ('student', 'teacher')) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS active_queues (
                    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER NOT NULL,
                    subject_name TEXT NOT NULL,
                    classroom TEXT NOT NULL,
                    status TEXT CHECK(status IN ('active', 'paused', 'closed')) DEFAULT 'active',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES users(telegram_id)
                );

                CREATE TABLE IF NOT EXISTS queue_records (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    lab_id INTEGER NOT NULL,
                    lab_difficulty INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    status TEXT CHECK(status IN ('waiting', 'called', 'protecting', 'passed', 'skipped')) DEFAULT 'waiting',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    called_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    FOREIGN KEY (queue_id) REFERENCES active_queues(queue_id),
                    FOREIGN KEY (student_id) REFERENCES users(telegram_id)
                );

                CREATE TABLE IF NOT EXISTS defense_history (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    lab_id INTEGER NOT NULL,
                    lab_difficulty INTEGER NOT NULL,
                    duration_minutes REAL NOT NULL,
                    time_elapsed_minutes REAL NOT NULL,
                    score INTEGER,
                    defense_date DATE DEFAULT CURRENT_DATE
                );
            """)

            await db.commit()

    async def add_student_to_queue(
        self, queue_id: int, student_id: int, lab_id: int, lab_difficulty: int
    ) -> int:
        """
        Добавляет студента в очередь и возвращает его позицию в очереди.
            - Если очередь не существует, выбрасывает исключение.
            - Если студент уже в очереди, возвращает его текущую позицию.

        :param queue_id: ID очереди, в которую добавляется студент
        :param student_id: Уникальный ID студента (telegram_id)
        :param lab_id: ID лабораторной работы
        :param lab_difficulty: Сложность лабораторной работы (1-3)

        :return: Позиция студента в очереди (int)
        """

        async with aiosqlite.connect(self.db_path) as db:
            # Получаем максимальную позицию в очереди для данного queue_id
            async with db.execute(
                "SELECT COALESCE(MAX(position), 0) FROM queue_records WHERE queue_id = ?",
                (queue_id,),
            ) as cursor:
                row = await cursor.fetchone()
                new_position = row[0] + 1

            await db.execute(
                """
                INSERT INTO queue_records (queue_id, student_id, lab_id, lab_difficulty, position, status)
                VALUES (?, ?, ?, ?, ?, 'waiting')
                """,
                (queue_id, student_id, lab_id, lab_difficulty, new_position),
            )
            await db.commit()
            return new_position

    async def get_active_queue(self, queue_id: int) -> List[Dict[str, Any]]:
        """
        Получает список студентов в активной очереди с их данными.
            - Возвращает только студентов со статусом 'waiting', 'called' или 'protecting', отсортированных по позиции в очереди.

        :param queue_id: ID очереди для получения данных

        :return: Список словарей с данными студентов в очереди
        """

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT student_id, lab_difficulty, position, status 
                FROM queue_records 
                WHERE queue_id = ? AND status IN ('waiting', 'called', 'protecting')
                ORDER BY position ASC
                """,
                (queue_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_student_status(self, record_id: int, new_status: str):
        """Обновляет статус студента в очереди и устанавливает соответствующие временные метки.
        - Если новый статус 'called', устанавливает called_at в текущее время.
        - Если новый статус 'passed' или 'skipped', устанавливает finished_at в текущее время.
        - Иначе, обновляет только статус без изменения временных меток.

        :param record_id: ID записи в queue_records для обновления
        :param new_status: Новый статус студента ('waiting', 'called', 'protecting', 'passed', 'skipped')
        """

        async with aiosqlite.connect(self.db_path) as db:
            update_fields = ["status = ?"]
            params = [new_status]

            if new_status == "called":
                update_fields.append("called_at = CURRENT_TIMESTAMP")
            elif new_status in ("passed", "skipped"):
                update_fields.append("finished_at = CURRENT_TIMESTAMP")

            query = f"UPDATE queue_records SET {', '.join(update_fields)} WHERE record_id = ?"
            params.append(record_id)

            await db.execute(query, params)
            await db.commit()

    async def create_queue(
        self, teacher_id: int, subject_name: str, classroom: str
    ) -> int:
        """
        Создает новую активную очередь и возвращает ее ID.

        :param teacher_id: Уникальный ID преподавателя (telegram_id)
        :param subject_name: Название предмета
        :param classroom: Аудитория проведения защиты
        :return: ID созданной очереди (int)
        """

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO active_queues (teacher_id, subject_name, classroom, status)
                VALUES (?, ?, ?, 'active')
                """,
                (teacher_id, subject_name, classroom),
            )
            await db.commit()
            return cursor.lastrowid

    async def call_next_student(self, queue_id: int) -> Optional[Dict[str, Any]]:
        """
        Переводит следующего ожидающего студента в статус 'called' и возвращает данные о нем.

         - Находит студента с наименьшей позицией в очереди и статусом 'waiting', обновляет его статус на 'called' и устанавливает called_at.
         - Если таких студентов нет, возвращает None.

         :param queue_id: ID очереди для вызова следующего студента
         :return: Словарь с данными вызванного студента или None, если очередь пуста
        """

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT record_id, student_id, position 
                FROM queue_records 
                WHERE queue_id = ? AND status = 'waiting' 
                ORDER BY position ASC LIMIT 1
                """,
                (queue_id,),
            ) as cursor:
                student = await cursor.fetchone()

            if student:
                await self.update_student_status(student["record_id"], "called")
                return dict(student)
            return None

    async def finish_defense(self, record_id: int, score: Optional[int] = None):
        """
        Завершает защиту, рассчитывает длительность и записывает данные в историю для переобучения.

         - Получает данные о студенте и его вызове из queue_records и active_queues.
         - Если студент не был вызван (called_at is NULL), просто обновляет статус на 'passed' и выходит.
         - Если студент был вызван, рассчитывает длительность защиты и время с начала пары, затем записывает эти данные в таблицу defense_history вместе с оценкой (если предоставлена).
         - Обновляет статус студента на 'passed' после завершения.

         :param record_id: ID записи в queue_records для завершения защиты
         :param score: Оценка за защиту (если предоставлена)
        """

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # 1. Получаем детали записи перед завершением
            async with db.execute(
                """
                SELECT qr.queue_id, qr.student_id, qr.lab_id, qr.lab_difficulty, 
                       qr.called_at, aq.teacher_id, aq.started_at
                FROM queue_records qr
                JOIN active_queues aq ON qr.queue_id = aq.queue_id
                WHERE qr.record_id = ?
                """,
                (record_id,),
            ) as cursor:
                record = await cursor.fetchone()

            if not record or not record["called_at"]:
                await self.update_student_status(record_id, "passed")
                return

            # 2. Обновляем статус на passed
            await self.update_student_status(record_id, "passed")

            # 3. Рассчитываем длительность и время с начала пары (в минутах)
            async with db.execute(
                """
                SELECT 
                    (strftime('%s', 'now') - strftime('%s', ?)) / 60.0 as duration,
                    (strftime('%s', 'now') - strftime('%s', ?)) / 60.0 as elapsed
                """,
                (record["called_at"], record["started_at"]),
            ) as cursor:
                times = await cursor.fetchone()

            # 4. Записываем в defense_history
            await db.execute(
                """
                INSERT INTO defense_history 
                (teacher_id, student_id, lab_id, lab_difficulty, duration_minutes, time_elapsed_minutes, score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["teacher_id"],
                    record["student_id"],
                    record["lab_id"],
                    record["lab_difficulty"],
                    max(0.1, times["duration"]),
                    times["elapsed"],
                    score,
                ),
            )
            await db.commit()

    async def close_queue(self, queue_id: int):
        """
        Закрывает всю очередь (конец пары)
            - Обновляет статус очереди на 'closed' в active_queues.
            - Опционально: обновляет статус всех студентов, которые не успели защититься, на 'skipped' в queue_records.

            :param queue_id: ID очереди для закрытия
            :return: None
        """

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE active_queues SET status = 'closed' WHERE queue_id = ?",
                (queue_id,),
            )
            # Опционально: отменяем всех, кто не успел сдаться
            await db.execute(
                "UPDATE queue_records SET status = 'skipped' WHERE queue_id = ? AND status = 'waiting'",
                (queue_id,),
            )
            await db.commit()

    async def save_user(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str,
        role: str,
    ):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO users
                (telegram_id, username, full_name, role)
                VALUES (?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    username,
                    full_name,
                    role,
                ),
            )

            await db.commit()

    async def get_user(
        self,
        telegram_id: int,
    ):
        async with aiosqlite.connect(self.db_path) as db:

            db.row_factory = aiosqlite.Row

            async with db.execute(
                """
                SELECT *
                FROM users
                WHERE telegram_id = ?
                """,
                (telegram_id,),
            ) as cursor:

                row = await cursor.fetchone()

                return dict(row) if row else None
