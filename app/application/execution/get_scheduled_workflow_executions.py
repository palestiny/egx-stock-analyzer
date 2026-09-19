from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

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


class GetScheduledWorkflowExecutions:
    def __init__(self, store: ScheduledWorkflowExecutionStore) -> None:
        self._store = store

    def execute(
        self,
        occurrence_id: str | None = None,
    ) -> tuple[ScheduledWorkflowExecutionReadModel, ...]:
        if occurrence_id is None:
            executions = self._store.list_all()
        else:
            execution = self._store.get_by_occurrence(occurrence_id)
            executions = () if execution is None else (execution,)

        return tuple(self._to_read_model(item) for item in executions)

    @staticmethod
    def _to_read_model(
        execution: ScheduledWorkflowExecution,
    ) -> ScheduledWorkflowExecutionReadModel:
        return ScheduledWorkflowExecutionReadModel(
            id=execution.id,
            occurrence_id=execution.occurrence_id,
            state=execution.state,
            created_at=execution.created_at,
            updated_at=execution.updated_at,
            analysis_state=execution.analysis_state,
            delivery_state=execution.delivery_state,
        )
