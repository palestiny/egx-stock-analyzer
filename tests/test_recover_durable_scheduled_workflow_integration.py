from datetime import date, datetime, timezone
from unittest.mock import Mock

from app.application.execution.recover_durable_scheduled_workflow import (
    RecoverDurableScheduledWorkflow,
)
from app.application.execution.run_durable_scheduled_workflow import (
    RunDurableScheduledWorkflow,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecutionState,
)
from app.application.notifications.automatic_alert_delivery import (
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


def make_analysis_execution() -> Execution:
    execution = Execution.create()
    execution.start()
    execution.record_stock_success("EGAL")
    execution.finish()
    return execution


def make_operation_result():
    return type(
        "Result",
        (),
        {
            "analysis_execution": make_analysis_execution(),
            "delivery_result": type(
                "Delivery",
                (),
                {
                    "state": AutomaticAlertDeliveryState.COMPLETED,
                },
            )(),
        },
    )()


def test_recovery_replays_interrupted_workflow_with_same_identity(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    clock = FakeClock()
    created = store.create_or_get("occurrence-1", clock.now())
    running = created.start(clock.now())
    store.save(running)
    interrupted = running.interrupt(clock.now())
    store.save(interrupted)

    operation = Mock()
    operation.execute.return_value = make_operation_result()
    workflow = RunDurableScheduledWorkflow(operation, store, clock)

    result = RecoverDurableScheduledWorkflow(workflow, store).execute(
        interrupted.id,
        date(2026, 9, 19),
    )

    assert result.id == interrupted.id
    assert result.state is ScheduledWorkflowExecutionState.COMPLETED
    operation.execute.assert_called_once_with(date(2026, 9, 19))


def test_terminal_recovery_is_idempotent_by_rejection(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    clock = FakeClock()
    created = store.create_or_get("occurrence-1", clock.now())
    completed = created.start(clock.now()).complete(clock.now())
    store.save(completed)

    operation = Mock()
    workflow = RunDurableScheduledWorkflow(operation, store, clock)
    recovery = RecoverDurableScheduledWorkflow(workflow, store)

    from app.application.execution.recover_durable_scheduled_workflow import (
        WorkflowExecutionNotRecoverableError,
    )

    try:
        recovery.execute(completed.id, date(2026, 9, 19))
    except WorkflowExecutionNotRecoverableError:
        pass
    else:
        raise AssertionError("Expected terminal execution to be rejected")

    operation.execute.assert_not_called()


def test_replay_failure_is_not_misclassified_as_recovery_validation_error(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    clock = FakeClock()
    created = store.create_or_get("occurrence-1", clock.now())
    running = created.start(clock.now())
    store.save(running)
    interrupted = running.interrupt(clock.now())
    store.save(interrupted)

    operation = Mock()
    operation.execute.side_effect = RuntimeError("replay failed")
    workflow = RunDurableScheduledWorkflow(operation, store, clock)

    recovery = RecoverDurableScheduledWorkflow(workflow, store)

    try:
        recovery.execute(interrupted.id, date(2026, 9, 19))
    except RuntimeError as exc:
        assert str(exc) == "replay failed"
    else:
        raise AssertionError("Expected replay failure")

    assert store.get(interrupted.id).state is ScheduledWorkflowExecutionState.FAILED
