from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import AuthenticatedIdentity
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
)


@dataclass(frozen=True)
class ScheduledWorkflowExecutionReadModel:
    id: UUID
    occurrence_id: str
    state: ScheduledWorkflowExecutionState
    created_at: datetime
    updated_at: datetime
    analysis_state: str | None
    delivery_state: str | None
    owner_user_id: UUID | None = None


class GetScheduledWorkflowExecutions:
    def __init__(self, store: ScheduledWorkflowExecutionStore) -> None:
        self._store = store
        self._authorizer = OwnershipAuthorizer()

    def execute(
        self,
        occurrence_id: str | None = None,
        identity: AuthenticatedIdentity | None = None,
    ) -> tuple[ScheduledWorkflowExecutionReadModel, ...]:
        if occurrence_id is None:
            executions = self._store.list_all()
            if identity is not None:
                executions = tuple(
                    execution
                    for execution in executions
                    if self._is_visible(execution, identity)
                )
        else:
            execution = self._store.get_by_occurrence(occurrence_id)
            if execution is None:
                executions = ()
            else:
                if identity is not None:
                    self._authorizer.require_owner_or_global(
                        identity,
                        execution.owner_user_id,
                    )
                executions = (execution,)

        return tuple(self._to_read_model(item) for item in executions)

    def _is_visible(
        self,
        execution: ScheduledWorkflowExecution,
        identity: AuthenticatedIdentity,
    ) -> bool:
        try:
            self._authorizer.require_owner_or_global(identity, execution.owner_user_id)
        except AuthorizationError:
            return False
        return True

    @staticmethod
    def _to_read_model(execution: ScheduledWorkflowExecution) -> ScheduledWorkflowExecutionReadModel:
        return ScheduledWorkflowExecutionReadModel(
            id=execution.id,
            occurrence_id=execution.occurrence_id,
            state=execution.state,
            created_at=execution.created_at,
            updated_at=execution.updated_at,
            owner_user_id=execution.owner_user_id,
            analysis_state=execution.analysis_state,
            delivery_state=execution.delivery_state,
        )
