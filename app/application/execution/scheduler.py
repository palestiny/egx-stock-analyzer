from collections.abc import Callable
from datetime import datetime
from typing import Protocol


class Scheduler(Protocol):
    def schedule(self, operation: Callable[[], object], run_at: datetime) -> None:
        ...


class InProcessScheduler:
    def __init__(self) -> None:
        self._pending_operations: list[tuple[datetime, Callable[[], object]]] = []

    def schedule(self, operation: Callable[[], object], run_at: datetime) -> None:
        self._pending_operations.append((run_at, operation))

    def pending_count(self) -> int:
        return len(self._pending_operations)

    def run_due(self, now: datetime) -> None:
        due = [
            operation
            for run_at, operation in self._pending_operations
            if run_at <= now
        ]
        self._pending_operations = [
            (run_at, operation)
            for run_at, operation in self._pending_operations
            if run_at > now
        ]

        for operation in due:
            operation()
