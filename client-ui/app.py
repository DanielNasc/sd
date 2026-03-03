import os
import uuid

from flask import Flask, redirect, render_template, request, session, url_for

from middleware.rpc_client import CircuitBreakerOpenError, RpcMiddleware

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-change-me")
rpc = RpcMiddleware()


def get_client_id() -> str:
    if "client_id" not in session:
        session["client_id"] = f"client-{uuid.uuid4().hex[:8]}"
    return session["client_id"]


def get_client_clock() -> int:
    return int(session.get("client_clock", 0))


def sync_client_clock(server_clock: int) -> None:
    local = get_client_clock()
    session["client_clock"] = max(local, int(server_clock)) + 1


@app.get("/")
def index():
    client_id = get_client_id()
    message = session.pop("message", "")
    error = session.pop("error", "")

    tasks = []
    server_clock = "offline"
    try:
        tasks = rpc.call("list_tasks")
        server_clock = rpc.call("get_server_clock")
    except Exception as err:
        error = str(err)

    return render_template(
        "index.html",
        tasks=tasks,
        client_id=client_id,
        client_clock=get_client_clock(),
        server_clock=server_clock,
        circuit_state=rpc.state,
        message=message,
        error=error,
    )


@app.post("/tasks")
def create_task():
    title = request.form.get("title", "")
    client_id = get_client_id()

    try:
        response = rpc.call("create_task", client_id, title, get_client_clock())
        if response.get("ok"):
            sync_client_clock(response["server_clock"])
            session["message"] = "Tarefa criada com sucesso."
        else:
            session["error"] = response.get("error", "Erro ao criar tarefa.")
    except CircuitBreakerOpenError as err:
        session["error"] = str(err)
    except Exception as err:
        session["error"] = str(err)

    return redirect(url_for("index"))


@app.post("/tasks/<int:task_id>/toggle")
def toggle_task(task_id: int):
    client_id = get_client_id()

    try:
        response = rpc.call("toggle_task", client_id, task_id, get_client_clock())
        if response.get("ok"):
            sync_client_clock(response["server_clock"])
            session["message"] = "Tarefa atualizada com sucesso."
        else:
            session["error"] = response.get("error", "Erro ao atualizar tarefa.")
    except CircuitBreakerOpenError as err:
        session["error"] = str(err)
    except Exception as err:
        session["error"] = str(err)

    return redirect(url_for("index"))


@app.post("/tasks/<int:task_id>/delete")
def delete_task(task_id: int):
    client_id = get_client_id()

    try:
        response = rpc.call("delete_task", client_id, task_id, get_client_clock())
        if response.get("ok"):
            sync_client_clock(response["server_clock"])
            session["message"] = "Tarefa removida com sucesso."
        else:
            session["error"] = response.get("error", "Erro ao remover tarefa.")
    except CircuitBreakerOpenError as err:
        session["error"] = str(err)
    except Exception as err:
        session["error"] = str(err)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
