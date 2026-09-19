from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol
from uuid import UUID, uuid4


class ScheduledWorkflowExecutionState(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class ScheduledWorkflowExecution:
    id: UUID
    occurrence_id: str
    state: ScheduledWorkflowExecutionState
    created_at: datetime
    updated_at: datetime
    analysis_state: str | None = None
    delivery_state: str | None = None

    @classmethod
    def create(
        cls,
        occurrence_id: str,
        now: datetime,
    ) -> "ScheduledWorkflowExecution":
        if not occurrence_id.strip():
            raise ValueError("occurrence_id cannot be empty")
        return cls(
            id=uuid4(),
            occurrence_id=occurrence_id,
            state=ScheduledWorkflowExecutionState.CREATED,
            created_at=now,
            updated_at=now,
            analysis_state=None,
            delivery_state=None,
        )

    def start(self, now: datetime) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.CREATED)
        return self._with_state(ScheduledWorkflowExecutionState.RUNNING, now)

    def start_recovery(self, now: datetime) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.INTERRUPTED)
        return self._with_state(ScheduledWorkflowExecutionState.RUNNING, now)

    def complete(self, now: datetime) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return self._with_state(ScheduledWorkflowExecutionState.COMPLETED, now)

    def complete_with_errors(self, now: datetime) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return self._with_state(
            ScheduledWorkflowExecutionState.COMPLETED_WITH_ERRORS,
            now,
        )

    def fail(self, now: datetime) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return self._with_state(ScheduledWorkflowExecutionState.FAILED, now)

    def interrupt(self, now: datetime) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return self._with_state(ScheduledWorkflowExecutionState.INTERRUPTED, now)

    def with_outcomes(
        self,
        analysis_state: str,
        delivery_state: str | None,
        now: datetime,
    ) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return ScheduledWorkflowExecution(
            id=self.id,
            occurrence_id=self.occurrence_id,
            state=self.state,
            created_at=self.created_at,
            updated_at=now,
            analysis_state=analysis_state,
            delivery_state=delivery_state,
        )

    def _with_state(
        self,
        state: ScheduledWorkflowExecutionState,
        now: datetime,
    ) -> "ScheduledWorkflowExecution":
        return ScheduledWorkflowExecution(
            id=self.id,
            occurrence_id=self.occurrence_id,
            state=state,
            created_at=self.created_at,
            updated_at=now,
            analysis_state=self.analysis_state,
            delivery_state=self.delivery_state,
        )

    def _require_state(self, expected: ScheduledWorkflowExecutionState) -> None:
        if self.state is not expected:
            raise ValueError(
                f"Workflow execution must be {expected.value}, "
                f"but is {self.state.value}"
            )


class ScheduledWorkflowExecutionStore(Protocol):
    def create_or_get(
        self,
        occurrence_id: str,
        now: datetime,
    ) -> ScheduledWorkflowExecution:
        ...

    def save(self, execution: ScheduledWorkflowExecution) -> None:
        ...

    def get_by_occurrence(
        self,
        occurrence_id: str,
    ) -> ScheduledWorkflowExecution | None:
        ...

    def get(self, execution_id: UUID) -> ScheduledWorkflowExecution | None:
        ...

    def recover_running(
        self,
        now: datetime,
    ) -> tuple[ScheduledWorkflowExecution, ...]:
        ...
