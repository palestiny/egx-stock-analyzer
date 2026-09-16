from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4


class ExecutionState(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Execution:
    id: UUID
    state: ExecutionState

    @classmethod
    def create(cls):
        return cls(id=uuid4(), state=ExecutionState.CREATED)

    def start(self):
        if self.state != ExecutionState.CREATED:
            raise ValueError("Execution can only start from CREATED")
        self.state = ExecutionState.RUNNING

    def complete(self):
        if self.state != ExecutionState.RUNNING:
            raise ValueError("Execution can only be completed when RUNNING")
        self.state = ExecutionState.COMPLETED

    def complete_with_errors(self):
        if self.state != ExecutionState.RUNNING:
            raise ValueError("Execution can only be completed with errors when RUNNING")
        self.state = ExecutionState.COMPLETED_WITH_ERRORS

    def fail(self):
        if self.state != ExecutionState.RUNNING:
            raise ValueError("Execution can only fail when RUNNING")
        self.state = ExecutionState.FAILED

    def cancel(self):
        if self.state != ExecutionState.RUNNING:
            raise ValueError("Execution can only be cancelled when RUNNING")
        self.state = ExecutionState.CANCELLED
