from collections.abc import Callable
from typing import Protocol


class Scheduler(Protocol):
    def schedule(self, operation: Callable[[], object]) -> None:
        ...


class InProcessScheduler:
    def __init__(self) -> None:
        self._pending_operations: list[Callable[[], object]] = []

    def schedule(self, operation: Callable[[], object]) -> None:
        self._pending_operations.append(operation)

    def pending_count(self) -> int:
        return len(self._pending_operations)

    def run_next(self) -> object:
        if not self._pending_operations:
            raise ValueError("No pending operations")

        operation = self._pending_operations.pop(0)
        return operation()
