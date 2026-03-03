import os
import threading
import time
from enum import Enum
from typing import Any
from xmlrpc.client import Fault, ProtocolError, ServerProxy


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(RuntimeError):
    pass


class RpcMiddleware:
    def __init__(self) -> None:
        self.server_url = os.getenv("RPC_SERVER_URL", "http://rpc-server:9000")
        self.max_retries = int(os.getenv("RPC_MAX_RETRIES", "3"))
        self.base_backoff = float(os.getenv("RPC_BASE_BACKOFF", "0.25"))
        self.failure_threshold = int(os.getenv("CB_FAILURE_THRESHOLD", "3"))
        self.recovery_timeout = float(os.getenv("CB_RECOVERY_TIMEOUT", "5"))

        self._failures = 0
        self._opened_since = 0.0
        self._state = CircuitState.CLOSED
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        return self._state.value

    def _can_attempt(self) -> None:
        with self._lock:
            if self._state != CircuitState.OPEN:
                return

            elapsed = time.time() - self._opened_since
            if elapsed >= self.recovery_timeout:
                # Apos timeout, permite uma tentativa de recuperacao (half-open).
                self._state = CircuitState.HALF_OPEN
                return

            raise CircuitBreakerOpenError("Circuit breaker aberto: servidor temporariamente indisponivel.")

    def _record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED

    def _record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_since = time.time()

    def call(self, method_name: str, *args: Any) -> Any:
        # Ponto unico de acesso RPC usado pela camada de apresentacao.
        self._can_attempt()

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with ServerProxy(self.server_url, allow_none=True) as proxy:
                    method = getattr(proxy, method_name)
                    response = method(*args)
                self._record_success()
                return response
            except (OSError, ConnectionError, TimeoutError, ProtocolError, Fault) as err:
                last_error = err
                self._record_failure()
                if attempt < self.max_retries:
                    # Backoff linear simples para reduzir explosao de tentativas.
                    time.sleep(self.base_backoff * attempt)

        if last_error:
            raise RuntimeError(f"Falha na chamada RPC '{method_name}': {last_error}") from last_error
        raise RuntimeError(f"Falha na chamada RPC '{method_name}'.")
