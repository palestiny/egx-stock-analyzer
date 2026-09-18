from dataclasses import dataclass, field
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
    successful_stock_ids: set[str] = field(default_factory=set)
    failed_stock_ids: set[str] = field(default_factory=set)
    failure_reasons: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls):
        return cls(id=uuid4(), state=ExecutionState.CREATED)

    def start(self):
        if self.state != ExecutionState.CREATED:
            raise ValueError("Execution can only start from CREATED")
        self.state = ExecutionState.RUNNING

    def record_stock_success(self, stock_id: str):
        if self.state != ExecutionState.RUNNING:
            raise ValueError("Stock results can only be recorded when RUNNING")
        self.successful_stock_ids.add(stock_id)
        self.failed_stock_ids.discard(stock_id)
        self.failure_reasons.pop(stock_id, None)

    def record_stock_failure(self, stock_id: str, reason: str | None = None):
        if self.state != ExecutionState.RUNNING:
            raise ValueError("Stock results can only be recorded when RUNNING")
        self.failed_stock_ids.add(stock_id)
        self.successful_stock_ids.discard(stock_id)
        if reason is not None:
            self.failure_reasons[stock_id] = reason

    def finish(self):
        if self.state != ExecutionState.RUNNING:
            raise ValueError("Execution can only be finished when RUNNING")

        if self.successful_stock_ids and not self.failed_stock_ids:
            self.state = ExecutionState.COMPLETED
        elif self.successful_stock_ids and self.failed_stock_ids:
            self.state = ExecutionState.COMPLETED_WITH_ERRORS
        else:
            self.state = ExecutionState.FAILED

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
