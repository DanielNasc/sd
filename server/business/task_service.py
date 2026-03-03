from datetime import datetime, timezone
from threading import Lock
from typing import Any

from domain.lamport import LamportClock
from persistence.repository import TaskRepository


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository
        self.clock = LamportClock()
        # Serializa operacoes de escrita para evitar corrida em recurso compartilhado.
        self.write_lock = Lock()

    def ping(self) -> str:
        return "pong"

    def get_server_clock(self) -> int:
        return self.clock.value

    def list_tasks(self) -> list[dict[str, Any]]:
        return self.repository.list_tasks()

    def create_task(self, client_id: str, title: str, client_clock: int) -> dict[str, Any]:
        if not title.strip():
            return {"ok": False, "error": "Titulo da tarefa nao pode ser vazio."}

        with self.write_lock:
            # Relogio logico de Lamport: recebe evento remoto e avanca clock do servidor.
            server_clock = self.clock.receive_event(client_clock)
            now_iso = datetime.now(timezone.utc).isoformat()
            task = self.repository.create_task(title.strip(), client_id, server_clock, now_iso)

        return {"ok": True, "task": task, "server_clock": server_clock}

    def toggle_task(self, client_id: str, task_id: int, client_clock: int) -> dict[str, Any]:
        with self.write_lock:
            server_clock = self.clock.receive_event(client_clock)
            now_iso = datetime.now(timezone.utc).isoformat()
            task = self.repository.toggle_task(task_id, client_id, server_clock, now_iso)

        if task is None:
            return {"ok": False, "error": "Tarefa nao encontrada.", "server_clock": server_clock}

        return {"ok": True, "task": task, "server_clock": server_clock}

    def delete_task(self, client_id: str, task_id: int, client_clock: int) -> dict[str, Any]:
        with self.write_lock:
            server_clock = self.clock.receive_event(client_clock)
            now_iso = datetime.now(timezone.utc).isoformat()
            deleted = self.repository.delete_task(task_id, client_id, server_clock, now_iso)

        if not deleted:
            return {"ok": False, "error": "Tarefa nao encontrada.", "server_clock": server_clock}

        return {"ok": True, "server_clock": server_clock}
