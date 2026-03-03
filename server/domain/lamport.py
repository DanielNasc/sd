from threading import Lock


class LamportClock:
    def __init__(self) -> None:
        self._value = 0
        self._lock = Lock()

    def tick(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def receive_event(self, external_clock: int) -> int:
        with self._lock:
            self._value = max(self._value, external_clock) + 1
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value
