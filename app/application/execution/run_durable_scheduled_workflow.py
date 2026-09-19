from datetime import date, datetime, timezone
from typing import Protocol

from app.application.execution.run_configured_market_analysis_with_automatic_alert_delivery import ConfiguredMarketAnalysisDeliveryResult
from app.application.execution.scheduled_workflow_execution import ScheduledWorkflowExecution, ScheduledWorkflowExecutionState, ScheduledWorkflowExecutionStore


class WorkflowClock(Protocol):
    def now(self) -> datetime: ...


class UtcWorkflowClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class RunDurableScheduledWorkflow:
    def __init__(self, scheduled_operation, store: ScheduledWorkflowExecutionStore, clock: WorkflowClock | None = None) -> None:
        self._scheduled_operation = scheduled_operation
        self._store = store
        self._clock = clock or UtcWorkflowClock()

    def execute(self, occurrence_id: str, as_of: date) -> ScheduledWorkflowExecution:
        execution = self._store.create_or_get(occurrence_id, self._clock.now())
        if execution.state is not ScheduledWorkflowExecutionState.CREATED:
            return execution
        return self._run(execution, as_of)

    def recover(self, execution_id, as_of: date) -> ScheduledWorkflowExecution:
        execution = self._store.get(execution_id)
        if execution is None:
            raise ValueError(f"Unknown scheduled workflow execution: {execution_id}")
        if execution.state is not ScheduledWorkflowExecutionState.INTERRUPTED:
            raise ValueError(f"Scheduled workflow execution is not interrupted: {execution.state.value}")
        return self._run(execution.start_recovery(self._clock.now()), as_of)

    def _run(self, execution: ScheduledWorkflowExecution, as_of: date) -> ScheduledWorkflowExecution:
        self._store.save(execution)
        try:
            result: ConfiguredMarketAnalysisDeliveryResult = self._scheduled_operation.execute(as_of)
        except Exception:
            failed = execution.fail(self._clock.now())
            self._store.save(failed)
            raise

        delivery_state = result.delivery_result.state.value if result.delivery_result is not None else None
        execution = execution.with_outcomes(result.analysis_execution.state.value, delivery_state, self._clock.now())
        self._store.save(execution)
        execution = getattr(execution, self._terminal_state(result))(self._clock.now())
        self._store.save(execution)
        return execution

    @staticmethod
    def _terminal_state(result: ConfiguredMarketAnalysisDeliveryResult) -> str:
        if result.analysis_execution.state.value == "failed":
            return "fail"
        if (result.analysis_execution.state.value == "completed_with_errors" or
            result.delivery_result is not None and result.delivery_result.state.value in {"completed_with_errors", "failed"}):
            return "complete_with_errors"
        return "complete"
