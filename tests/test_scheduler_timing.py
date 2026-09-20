from datetime import datetime, timezone
from unittest.mock import Mock

from app.application.execution.scheduler import InProcessScheduler


def test_scheduler_runs_operation_when_due():
    operation = Mock()
    scheduler = InProcessScheduler()
    run_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    scheduler.schedule(operation, run_at)

    assert scheduler.pending_count() == 1
    scheduler.run_due(run_at)

    operation.assert_called_once_with()
    assert scheduler.pending_count() == 0


def test_scheduler_does_not_run_operation_before_due():
    operation = Mock()
    scheduler = InProcessScheduler()
    run_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    before_due = datetime(2026, 1, 1, 11, 59, tzinfo=timezone.utc)

    scheduler.schedule(operation, run_at)

    scheduler.run_due(before_due)

    operation.assert_not_called()
    assert scheduler.pending_count() == 1
