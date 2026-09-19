from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.execution.get_scheduled_workflow_executions import (
    ScheduledWorkflowExecutionReadModel,
)
from app.application.execution.scheduled_workflow_execution import ScheduledWorkflowExecution


@dataclass(frozen=True)
class ScheduledWorkflowExecutionResponse:
    id: UUID
    occurrence_id: str
    state: str
    created_at: datetime
    updated_at: datetime
    analysis_state: str | None
    delivery_state: str | None
    owner_user_id: UUID | None

    @classmethod
    def from_execution(
        cls,
        execution: ScheduledWorkflowExecution,
    ) -> "ScheduledWorkflowExecutionResponse":
        return cls(
            id=execution.id,
            occurrence_id=execution.occurrence_id,
            state=execution.state.value,
            created_at=execution.created_at,
            updated_at=execution.updated_at,
            analysis_state=execution.analysis_state,
            delivery_state=execution.delivery_state,
            owner_user_id=execution.owner_user_id,
        )

    @classmethod
    def from_read_model(
        cls,
        item: ScheduledWorkflowExecutionReadModel,
    ) -> "ScheduledWorkflowExecutionResponse":
        return cls(
            id=item.id,
            occurrence_id=item.occurrence_id,
            state=item.state.value,
            created_at=item.created_at,
            updated_at=item.updated_at,
            analysis_state=item.analysis_state,
            delivery_state=item.delivery_state,
            owner_user_id=item.owner_user_id,
        )


@dataclass(frozen=True)
class ScheduledWorkflowExecutionsResponse:
    items: tuple[ScheduledWorkflowExecutionResponse, ...]

    @classmethod
    def from_items(
        cls,
        items: tuple[ScheduledWorkflowExecutionReadModel, ...],
    ) -> "ScheduledWorkflowExecutionsResponse":
        return cls(
            items=tuple(
                ScheduledWorkflowExecutionResponse.from_read_model(item)
                for item in items
            )
        )
