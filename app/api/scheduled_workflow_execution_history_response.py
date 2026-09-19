from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.execution.get_scheduled_workflow_execution_history import (
    ScheduledWorkflowExecutionHistoryReadModel,
)


@dataclass(frozen=True)
class ScheduledWorkflowExecutionHistoryItemResponse:
    sequence: int
    from_state: str | None
    to_state: str
    occurred_at: datetime
    reason: str | None


@dataclass(frozen=True)
class ScheduledWorkflowExecutionHistoryResponse:
    execution_id: UUID
    occurrence_id: str
    history: tuple[ScheduledWorkflowExecutionHistoryItemResponse, ...]
    has_more: bool = False
    next_cursor: str | None = None

    @classmethod
    def from_read_model(
        cls,
        read_model: ScheduledWorkflowExecutionHistoryReadModel,
    ) -> "ScheduledWorkflowExecutionHistoryResponse":
        return cls(
            execution_id=read_model.execution_id,
            occurrence_id=read_model.occurrence_id,
            has_more=read_model.has_more,
            next_cursor=read_model.next_cursor,
            history=tuple(
                ScheduledWorkflowExecutionHistoryItemResponse(
                    sequence=item.sequence,
                    from_state=item.from_state,
                    to_state=item.to_state,
                    occurred_at=item.occurred_at,
                    reason=item.reason,
                )
                for item in read_model.history
            ),
        )
