from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.execution.get_scheduled_workflow_history import (
    ScheduledWorkflowHistoryReadModel,
)


@dataclass(frozen=True)
class ScheduledWorkflowHistoryItemResponse:
    execution_id: UUID
    occurrence_id: str
    sequence: int
    from_state: str | None
    to_state: str
    occurred_at: datetime
    reason: str | None


@dataclass(frozen=True)
class ScheduledWorkflowHistoryResponse:
    items: tuple[ScheduledWorkflowHistoryItemResponse, ...]
    has_more: bool
    next_cursor: str | None

    @classmethod
    def from_read_model(
        cls,
        read_model: ScheduledWorkflowHistoryReadModel,
    ) -> "ScheduledWorkflowHistoryResponse":
        return cls(
            items=tuple(
                ScheduledWorkflowHistoryItemResponse(
                    execution_id=item.execution_id,
                    occurrence_id=item.occurrence_id,
                    sequence=item.sequence,
                    from_state=item.from_state,
                    to_state=item.to_state,
                    occurred_at=item.occurred_at,
                    reason=item.reason,
                )
                for item in read_model.items
            ),
            has_more=read_model.has_more,
            next_cursor=read_model.next_cursor,
        )
