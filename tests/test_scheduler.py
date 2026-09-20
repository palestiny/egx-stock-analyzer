from datetime import datetime, timezone
from unittest.mock import Mock

from app.application.execution.scheduler import InProcessScheduler


def test_scheduler_registers_operation_for_execution():
    operation = Mock()
    scheduler = InProcessScheduler()
    run_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    scheduler.schedule(operation, run_at)

    assert scheduler.pending_count() == 1
    scheduler.run_due(run_at)
    operation.assert_called_once_with()
    assert scheduler.pending_count() == 0
