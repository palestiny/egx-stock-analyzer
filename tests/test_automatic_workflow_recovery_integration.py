from datetime import date, datetime, timezone
from unittest.mock import Mock

from app.application.execution.automatic_workflow_recovery import (
    AutomaticWorkflowRecovery,
)
from app.application.execution.recover_durable_scheduled_workflow import (
    RecoverDurableScheduledWorkflow,
)
from app.application.execution.run_durable_scheduled_workflow import (
    RunDurableScheduledWorkflow,
)
from app.application.execution.scheduled_workflow_execution import (
    ScheduledWorkflowExecutionState,
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


def completed_analysis():
    execution = Execution.create()
    execution.start()
    execution.record_stock_success("EGAL")
    execution.finish()
    return execution


def test_startup_recovery_resumes_persisted_interrupted_execution(tmp_path):
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    created = store.create_or_get(
        "00000000-0000-0000-0000-000000000001:2026-09-19:08:30:00",
        datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
    )
    interrupted = created.start(
        datetime(2026, 9, 19, 7, 1, tzinfo=timezone.utc)
    ).interrupt(
        datetime(2026, 9, 19, 7, 2, tzinfo=timezone.utc)
    )
    store.save(interrupted)

    scheduled_operation = Mock()
    scheduled_operation.execute.return_value = type(
        "Result",
        (),
        {
            "analysis_execution": completed_analysis(),
            "delivery_result": None,
        },
    )()

    clock = FakeClock()
    durable_workflow = RunDurableScheduledWorkflow(
        scheduled_operation,
        store,
        clock,
    )
    recover = RecoverDurableScheduledWorkflow(durable_workflow, store)
    automatic = AutomaticWorkflowRecovery(recover, store)

    result = automatic.execute()

    assert result.attempted == (created.id,)
    assert result.recovered == (created.id,)
    assert result.failed == ()
    scheduled_operation.execute.assert_called_once_with(date(2026, 9, 19))

    restarted_store = SQLiteScheduledWorkflowExecutionStore(
        tmp_path / "workflow.db"
    )
    persisted = restarted_store.get(created.id)

    assert persisted is not None
    assert persisted.id == created.id
    assert persisted.state is ScheduledWorkflowExecutionState.COMPLETED
