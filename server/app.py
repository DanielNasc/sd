import os
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

from business.task_service import TaskService
from persistence.repository import TaskRepository


class RequestHandler(SimpleXMLRPCRequestHandler):
    # Restringe as chamadas RPC para o path padrao do XML-RPC.
    rpc_paths = ("/RPC2",)


class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    # MixIn de threads para atender clientes simultaneamente.
    pass


def main() -> None:
    host = os.getenv("RPC_HOST", "0.0.0.0")
    port = int(os.getenv("RPC_PORT", "9000"))
    db_path = os.getenv("DB_PATH", "/data/tasks.db")

    repository = TaskRepository(db_path)
    service = TaskService(repository)

    with ThreadedXMLRPCServer(
        (host, port),
        requestHandler=RequestHandler,
        allow_none=True,
        logRequests=True,
    ) as server:
        # Metodos expostos remotamente para o container cliente.
        server.register_introspection_functions()
        server.register_function(service.ping, "ping")
        server.register_function(service.get_server_clock, "get_server_clock")
        server.register_function(service.list_tasks, "list_tasks")
        server.register_function(service.create_task, "create_task")
        server.register_function(service.toggle_task, "toggle_task")
        server.register_function(service.delete_task, "delete_task")

        print(f"RPC server listening on {host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
