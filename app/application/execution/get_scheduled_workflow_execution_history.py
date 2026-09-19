from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionStore,
)
from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity


class ScheduledWorkflowExecutionHistoryNotFoundError(ValueError):
    """Raised when a requested scheduled workflow execution does not exist."""


@dataclass(frozen=True)
class ScheduledWorkflowExecutionHistoryItem:
    sequence: int
    from_state: str | None
    to_state: str
    occurred_at: datetime
    reason: str | None


@dataclass(frozen=True)
class ScheduledWorkflowExecutionHistoryReadModel:
    execution_id: UUID
    occurrence_id: str
    history: tuple[ScheduledWorkflowExecutionHistoryItem, ...]


class GetScheduledWorkflowExecutionHistory:
    def __init__(self, store: ScheduledWorkflowExecutionStore) -> None:
        self._store = store
        self._authorizer = OwnershipAuthorizer()

    def execute(
        self,
        execution_id: UUID,
        identity: AuthenticatedIdentity,
    ) -> ScheduledWorkflowExecutionHistoryReadModel:
        execution = self._store.get(execution_id)
        if execution is None:
            raise ScheduledWorkflowExecutionHistoryNotFoundError(
                f"Unknown scheduled workflow execution: {execution_id}"
            )

        self._authorizer.require_owner_or_global(
            identity,
            execution.owner_user_id,
        )

        history = tuple(
            ScheduledWorkflowExecutionHistoryItem(
                sequence=sequence,
                from_state=from_state,
                to_state=to_state,
                occurred_at=occurred_at,
                reason=reason,
            )
            for sequence, from_state, to_state, occurred_at, reason in self._store.get_history(
                execution_id
            )
        )

        return ScheduledWorkflowExecutionHistoryReadModel(
            execution_id=execution.id,
            occurrence_id=execution.occurrence_id,
            history=history,
        )
