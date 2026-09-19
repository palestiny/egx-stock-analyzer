from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.application.execution.recover_durable_scheduled_workflow import (
    RecoverDurableScheduledWorkflow,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
)


@dataclass(frozen=True)
class AutomaticWorkflowRecoveryResult:
    attempted: tuple[UUID, ...]
    recovered: tuple[UUID, ...]
    failed: tuple[UUID, ...]


class AutomaticWorkflowRecovery:
    """Recover eligible interrupted workflow executions during application startup."""

    def __init__(
        self,
        recover_workflow: RecoverDurableScheduledWorkflow,
        store: ScheduledWorkflowExecutionStore,
    ) -> None:
        self._recover_workflow = recover_workflow
        self._store = store

    def execute(self) -> AutomaticWorkflowRecoveryResult:
        executions = self._store.list_interrupted()

        attempted: list[UUID] = []
        recovered: list[UUID] = []
        failed: list[UUID] = []

        for execution in executions:
            attempted.append(execution.id)
            try:
                self._recover_workflow.execute(
                    execution.id,
                    self._as_of(execution),
                )
            except Exception:
                failed.append(execution.id)
            else:
                recovered.append(execution.id)

        return AutomaticWorkflowRecoveryResult(
            attempted=tuple(attempted),
            recovered=tuple(recovered),
            failed=tuple(failed),
        )

    @staticmethod
    def _as_of(execution: ScheduledWorkflowExecution) -> date:
        if execution.state is not ScheduledWorkflowExecutionState.INTERRUPTED:
            raise ValueError("Only interrupted executions can be automatically recovered")

        parts = execution.occurrence_id.split(":")
        if len(parts) < 3:
            raise ValueError(
                f"Invalid scheduled workflow occurrence id: {execution.occurrence_id}"
            )

        try:
            return date.fromisoformat(parts[1])
        except ValueError as error:
            raise ValueError(
                f"Invalid scheduled workflow occurrence date: {parts[1]}"
            ) from error
