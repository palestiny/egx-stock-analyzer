from datetime import date, datetime, timezone
from typing import Protocol

from app.application.execution.run_configured_market_analysis_with_automatic_alert_delivery import (
    ConfiguredMarketAnalysisDeliveryResult,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecution,
    ScheduledWorkflowExecutionState,
    ScheduledWorkflowExecutionStore,
)


class WorkflowClock(Protocol):
    def now(self) -> datetime:
        ...


class UtcWorkflowClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class RunDurableScheduledWorkflow:
    def __init__(
        self,
        scheduled_operation,
        store: ScheduledWorkflowExecutionStore,
        clock: WorkflowClock | None = None,
    ) -> None:
        self._scheduled_operation = scheduled_operation
        self._store = store
        self._clock = clock or UtcWorkflowClock()

    def execute(
        self,
        occurrence_id: str,
        as_of: date,
    ) -> ScheduledWorkflowExecution:
        execution = self._store.create_or_get(
            occurrence_id,
            self._clock.now(),
        )

        if execution.state is not ScheduledWorkflowExecutionState.CREATED:
            return execution

        execution = execution.start(self._clock.now())
        self._store.save(execution)

        try:
            result: ConfiguredMarketAnalysisDeliveryResult = (
                self._scheduled_operation.execute(as_of)
            )
        except Exception:
            failed = execution.fail(self._clock.now())
            self._store.save(failed)
            raise

        delivery_state = (
            result.delivery_result.state.value
            if result.delivery_result is not None
            else None
        )
        execution = execution.with_outcomes(
            analysis_state=result.analysis_execution.state.value,
            delivery_state=delivery_state,
            now=self._clock.now(),
        )
        self._store.save(execution)

        terminal_state = self._terminal_state(result)
        execution = getattr(execution, terminal_state)(self._clock.now())
        self._store.save(execution)
        return execution

    @staticmethod
    def _terminal_state(
        result: ConfiguredMarketAnalysisDeliveryResult,
    ) -> str:
        if result.analysis_execution.state.value == "failed":
            return "fail"

        if (
            result.analysis_execution.state.value == "completed_with_errors"
            or result.delivery_result is not None
            and result.delivery_result.state.value == "completed_with_errors"
            or result.delivery_result is not None
            and result.delivery_result.state.value == "failed"
        ):
            return "complete_with_errors"

        return "complete"
