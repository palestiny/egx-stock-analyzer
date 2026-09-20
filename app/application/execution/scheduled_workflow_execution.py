from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol
from uuid import UUID, uuid4


class ScheduledWorkflowExecutionIdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused with a different request fingerprint."""


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
    owner_user_id: UUID | None = None
    analysis_state: str | None = None
    delivery_state: str | None = None
    request_fingerprint: str | None = None
    revision: int = 0
    transition_reason: str | None = None

    @classmethod
    def create(
        cls,
        occurrence_id: str,
        now: datetime,
        owner_user_id: UUID | None = None,
        request_fingerprint: str | None = None,
    ) -> "ScheduledWorkflowExecution":
        if not occurrence_id.strip():
            raise ValueError("occurrence_id cannot be empty")
        return cls(
            id=uuid4(),
            occurrence_id=occurrence_id,
            state=ScheduledWorkflowExecutionState.CREATED,
            created_at=now,
            updated_at=now,
            owner_user_id=owner_user_id,
            request_fingerprint=request_fingerprint,
            revision=0,
        )

    def start(self, now: datetime, reason: str | None = None) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.CREATED)
        return self._with_state(ScheduledWorkflowExecutionState.RUNNING, now, reason)

    def start_recovery(
        self,
        now: datetime,
        reason: str | None = None,
    ) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.INTERRUPTED)
        return self._with_state(ScheduledWorkflowExecutionState.RUNNING, now, reason)

    def complete(self, now: datetime, reason: str | None = None) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return self._with_state(ScheduledWorkflowExecutionState.COMPLETED, now, reason)

    def complete_with_errors(
        self,
        now: datetime,
        reason: str | None = None,
    ) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return self._with_state(
            ScheduledWorkflowExecutionState.COMPLETED_WITH_ERRORS,
            now,
            reason,
        )

    def fail(self, now: datetime, reason: str | None = None) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return self._with_state(ScheduledWorkflowExecutionState.FAILED, now, reason)

    def interrupt(self, now: datetime, reason: str | None = None) -> "ScheduledWorkflowExecution":
        self._require_state(ScheduledWorkflowExecutionState.RUNNING)
        return self._with_state(ScheduledWorkflowExecutionState.INTERRUPTED, now, reason)

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
            owner_user_id=self.owner_user_id,
            analysis_state=analysis_state,
            delivery_state=delivery_state,
            request_fingerprint=self.request_fingerprint,
            revision=self.revision + 1,
            transition_reason=self.transition_reason,
        )

    def _with_state(
        self,
        state: ScheduledWorkflowExecutionState,
        now: datetime,
        reason: str | None,
    ) -> "ScheduledWorkflowExecution":
        return ScheduledWorkflowExecution(
            id=self.id,
            occurrence_id=self.occurrence_id,
            state=state,
            created_at=self.created_at,
            updated_at=now,
            owner_user_id=self.owner_user_id,
            analysis_state=self.analysis_state,
            delivery_state=self.delivery_state,
            request_fingerprint=self.request_fingerprint,
            revision=self.revision + 1,
            transition_reason=reason,
        )

    def _require_state(self, expected: ScheduledWorkflowExecutionState) -> None:
        if self.state is not expected:
            raise ValueError(
                f"Workflow execution must be {expected.value}, but is {self.state.value}"
            )


class ScheduledWorkflowExecutionStore(Protocol):
    def create_or_get(
        self,
        occurrence_id: str,
        now: datetime,
        owner_user_id: UUID | None = None,
        request_fingerprint: str | None = None,
    ) -> ScheduledWorkflowExecution:
        ...

    def save(self, execution: ScheduledWorkflowExecution) -> None:
        ...

    def start_if_created(
        self,
        execution_id: UUID,
        now: datetime,
    ) -> ScheduledWorkflowExecution | None:
        ...

    def get_by_occurrence(self, occurrence_id: str) -> ScheduledWorkflowExecution | None:
        ...

    def get(self, execution_id: UUID) -> ScheduledWorkflowExecution | None:
        ...

    def recover_running(self, now: datetime) -> tuple[ScheduledWorkflowExecution, ...]:
        ...

    def list_all(self) -> tuple[ScheduledWorkflowExecution, ...]:
        ...

    def list_interrupted(self) -> tuple[ScheduledWorkflowExecution, ...]:
        ...


    def get_history(
        self,
        execution_id: UUID,
        after_sequence: int | None = None,
        limit: int | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[tuple[int, str | None, str, datetime, str | None], ...]:
        ...
