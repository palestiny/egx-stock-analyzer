from datetime import date
from uuid import UUID

from app.application.execution.run_durable_scheduled_workflow import RunDurableScheduledWorkflow
from app.application.security.identity import AuthenticatedIdentity
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
)


class WorkflowExecutionNotFoundError(ValueError):
    """Raised when the requested workflow execution does not exist."""


class WorkflowExecutionNotRecoverableError(ValueError):
    """Raised when a workflow execution is not INTERRUPTED."""


class RecoverDurableScheduledWorkflow:
    def __init__(
        self,
        scheduled_workflow: RunDurableScheduledWorkflow,
        store: ScheduledWorkflowExecutionStore,
    ) -> None:
        self._scheduled_workflow = scheduled_workflow
        self._store = store

    def execute(
        self,
        execution_id: UUID,
        as_of: date,
        identity: AuthenticatedIdentity | None = None,
    ) -> ScheduledWorkflowExecution:
        execution = self._store.get(execution_id)
        if execution is None:
            raise WorkflowExecutionNotFoundError(
                f"Unknown scheduled workflow execution: {execution_id}"
            )

        if execution.state is not ScheduledWorkflowExecutionState.INTERRUPTED:
            raise WorkflowExecutionNotRecoverableError(
                "Scheduled workflow execution is not interrupted: "
                f"{execution.state.value}"
            )

        if identity is None:
            return self._scheduled_workflow.recover(execution_id, as_of)
        return self._scheduled_workflow.recover(execution_id, as_of, identity)
