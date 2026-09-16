from unittest.mock import Mock

from app.application.execution.scheduler import Scheduler


def test_scheduler_registers_operation_for_execution():
    operation = Mock()
    scheduler = Scheduler()

    scheduler.schedule(operation)

    assert scheduler.pending_count() == 1
    scheduler.run_next()
    operation.assert_called_once_with()
    assert scheduler.pending_count() == 0
