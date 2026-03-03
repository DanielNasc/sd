import sqlite3
from pathlib import Path
from typing import Any


class TaskRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    last_clock INTEGER NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    task_id INTEGER,
                    actor TEXT NOT NULL,
                    lamport_clock INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create_task(self, title: str, actor: str, lamport_clock: int, now_iso: str) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO tasks (title, done, last_clock, updated_by, updated_at)
                VALUES (?, 0, ?, ?, ?)
                """,
                (title, lamport_clock, actor, now_iso),
            )
            task_id = cur.lastrowid
            conn.execute(
                """
                INSERT INTO event_log (operation, task_id, actor, lamport_clock, created_at)
                VALUES ('CREATE', ?, ?, ?, ?)
                """,
                (task_id, actor, lamport_clock, now_iso),
            )
            task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(task)

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY done ASC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def toggle_task(
        self, task_id: int, actor: str, lamport_clock: int, now_iso: str
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                return None

            new_done = 0 if row["done"] else 1
            conn.execute(
                """
                UPDATE tasks
                SET done = ?, last_clock = ?, updated_by = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_done, lamport_clock, actor, now_iso, task_id),
            )
            conn.execute(
                """
                INSERT INTO event_log (operation, task_id, actor, lamport_clock, created_at)
                VALUES ('TOGGLE', ?, ?, ?, ?)
                """,
                (task_id, actor, lamport_clock, now_iso),
            )
            task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(task)

    def delete_task(self, task_id: int, actor: str, lamport_clock: int, now_iso: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cur.rowcount == 0:
                return False
            conn.execute(
                """
                INSERT INTO event_log (operation, task_id, actor, lamport_clock, created_at)
                VALUES ('DELETE', ?, ?, ?, ?)
                """,
                (task_id, actor, lamport_clock, now_iso),
            )
            return True
