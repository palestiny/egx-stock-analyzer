from datetime import date, datetime, time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID
from zoneinfo import ZoneInfo

from app.application.execution.recurring_configured_market_analysis import (
    RecurringConfiguredMarketAnalysis,
)
from app.application.execution.run_durable_scheduled_workflow import (
    RunDurableScheduledWorkflow,
)
from app.application.execution.scheduler import Scheduler
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)


CAIRO = ZoneInfo("Africa/Cairo")


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class FakeScheduler:
    def __init__(self) -> None:
        self.scheduled: list[tuple[datetime, object]] = []

    def schedule(self, operation, run_at: datetime) -> None:
        self.scheduled.append((run_at, operation))


def completed_result():
    return SimpleNamespace(
        analysis_execution=SimpleNamespace(
            state=SimpleNamespace(value="completed"),
        ),
        analysis_run_id=UUID("00000000-0000-0000-0000-000000000011"),
        delivery_result=SimpleNamespace(
            state=SimpleNamespace(value="completed"),
        ),
    )


def test_recurring_occurrence_is_persisted_through_durable_workflow(tmp_path):
    clock = FakeClock(datetime(2026, 9, 18, 20, 0, tzinfo=CAIRO))
    scheduler: Scheduler = FakeScheduler()
    scheduled_operation = Mock()
    scheduled_operation.execute.return_value = completed_result()
    store = SQLiteScheduledWorkflowExecutionStore(tmp_path / "workflow.db")
    durable_workflow = RunDurableScheduledWorkflow(
        scheduled_operation,
        store,
        clock,
    )
    recurring = RecurringConfiguredMarketAnalysis(
        durable_workflow,
        scheduler,
        clock,
        schedule_time=time(21, 0),
        schedule_id=UUID("11111111-1111-1111-1111-111111111111"),
    )

    recurring.start()
    clock.current = datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO)
    scheduler.scheduled[0][1]()

    import sqlite3

    with sqlite3.connect(tmp_path / "workflow.db") as connection:
        row = connection.execute(
            "SELECT occurrence_id, state, analysis_state, delivery_state "
            "FROM scheduled_workflow_executions"
        ).fetchone()

    assert row is not None
    occurrence_id, state, analysis_state, delivery_state = row
    assert state == "completed"
    assert analysis_state == "completed"
    assert delivery_state == "completed"
    assert occurrence_id == "11111111-1111-1111-1111-111111111111:2026-09-18:21:00:00"

    scheduled_operation.execute.assert_called_once_with(date(2026, 9, 18))
