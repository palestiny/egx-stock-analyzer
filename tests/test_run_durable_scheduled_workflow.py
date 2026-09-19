from datetime import date, datetime, timezone
from unittest.mock import Mock

from app.application.execution.run_durable_scheduled_workflow import (
    RunDurableScheduledWorkflow,
)
from app.application.notifications.automatic_alert_delivery import (
    AutomaticAlertDeliveryResult,
    AutomaticAlertDeliveryState,
)
from app.domain.execution import Execution, ExecutionState
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value


def make_execution(state: ExecutionState) -> Execution:
    execution = Execution.create()
    execution.start()

    if state is ExecutionState.COMPLETED:
        execution.record_stock_success("EGAL")
        execution.finish()
    elif state is ExecutionState.COMPLETED_WITH_ERRORS:
        execution.record_stock_success("EGAL")
        execution.record_stock_failure("IEEC", "failed")
        execution.finish()
    elif state is ExecutionState.FAILED:
        execution.record_stock_failure("EGAL", "failed")
        execution.finish()
    else:
        raise AssertionError(state)

    return execution


def make_delivery(state: AutomaticAlertDeliveryState) -> AutomaticAlertDeliveryResult:
    return AutomaticAlertDeliveryResult(
        state=state,
        attempted_count=1,
        delivered_count=1 if state is AutomaticAlertDeliveryState.COMPLETED else 0,
        skipped_count=0,
        failed_count=0 if state is AutomaticAlertDeliveryState.COMPLETED else 1,
        failure_reasons={},
    )


def test_completed_workflow_persists_independent_outcomes(tmp_path):
    operation = Mock()
    operation.execute.return_value = type(
        "Result",
        (),
        {
            "analysis_execution": make_execution(ExecutionState.COMPLETED),
            "delivery_result": make_delivery(AutomaticAlertDeliveryState.COMPLETED),
        },
    )()
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    workflow = RunDurableScheduledWorkflow(operation, store, FakeClock())

    result = workflow.execute("occurrence-1", date(2026, 9, 19))

    assert result.state.value == "completed"
    assert result.analysis_state == "completed"
    assert result.delivery_state == "completed"


def test_partial_analysis_completes_with_errors(tmp_path):
    operation = Mock()
    operation.execute.return_value = type(
        "Result",
        (),
        {
            "analysis_execution": make_execution(ExecutionState.COMPLETED_WITH_ERRORS),
            "delivery_result": make_delivery(AutomaticAlertDeliveryState.COMPLETED),
        },
    )()
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    workflow = RunDurableScheduledWorkflow(operation, store, FakeClock())

    result = workflow.execute("occurrence-1", date(2026, 9, 19))

    assert result.state.value == "completed_with_errors"


def test_delivery_failure_does_not_change_analysis_outcome(tmp_path):
    operation = Mock()
    operation.execute.return_value = type(
        "Result",
        (),
        {
            "analysis_execution": make_execution(ExecutionState.COMPLETED),
            "delivery_result": make_delivery(AutomaticAlertDeliveryState.FAILED),
        },
    )()
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    workflow = RunDurableScheduledWorkflow(operation, store, FakeClock())

    result = workflow.execute("occurrence-1", date(2026, 9, 19))

    assert result.state.value == "completed_with_errors"
    assert result.analysis_state == "completed"
    assert result.delivery_state == "failed"


def test_same_occurrence_is_not_executed_twice(tmp_path):
    operation = Mock()
    operation.execute.return_value = type(
        "Result",
        (),
        {
            "analysis_execution": make_execution(ExecutionState.COMPLETED),
            "delivery_result": make_delivery(AutomaticAlertDeliveryState.COMPLETED),
        },
    )()
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    workflow = RunDurableScheduledWorkflow(operation, store, FakeClock())

    first = workflow.execute("occurrence-1", date(2026, 9, 19))
    second = workflow.execute("occurrence-1", date(2026, 9, 19))

    assert first.id == second.id
    operation.execute.assert_called_once()


def test_analysis_exception_is_persisted_as_failed(tmp_path):
    operation = Mock()
    operation.execute.side_effect = RuntimeError("analysis failed")
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    workflow = RunDurableScheduledWorkflow(operation, store, FakeClock())

    try:
        workflow.execute("occurrence-1", date(2026, 9, 19))
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected analysis failure")

    stored = store.get_by_occurrence("occurrence-1")
    assert stored is not None
    assert stored.state is not None
    assert stored.state.value == "failed"
