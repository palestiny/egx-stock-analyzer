from datetime import date
from uuid import UUID

from app.application.execution.run_durable_scheduled_workflow import RunDurableScheduledWorkflow
from app.application.execution.scheduled_workflow_execution import ScheduledWorkflowExecution, ScheduledWorkflowExecutionState, ScheduledWorkflowExecutionStore


class WorkflowExecutionNotFoundError(ValueError):
    """Raised when the requested workflow execution does not exist."""


class WorkflowExecutionNotRecoverableError(ValueError):
    """Raised when a workflow execution is not INTERRUPTED."""


class RecoverDurableScheduledWorkflow:
    def __init__(self, scheduled_workflow: RunDurableScheduledWorkflow) -> None:
        self._scheduled_workflow = scheduled_workflow

    def execute(self, execution_id: UUID, as_of: date) -> ScheduledWorkflowExecution:
        try:
            return self._scheduled_workflow.recover(execution_id, as_of)
        except ValueError as exc:
            if str(exc).startswith("Unknown scheduled workflow execution"):
                raise WorkflowExecutionNotFoundError(str(exc)) from exc
            raise WorkflowExecutionNotRecoverableError(str(exc)) from exc
