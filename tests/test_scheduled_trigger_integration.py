from datetime import datetime, timezone
from unittest.mock import Mock

from app.application.execution.scheduled_trigger import ScheduledAnalysisTrigger
from app.application.execution.scheduler import InProcessScheduler
from app.domain.execution import Execution


def test_scheduled_trigger_runs_analysis_when_scheduler_reaches_due_time():
    inputs = [Mock()]
    expected_execution = Execution.create()
    expected_execution.start()
    run_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    before_due = datetime(2026, 1, 1, 11, 59, tzinfo=timezone.utc)

    analysis = Mock()
    analysis.run.return_value.execution = expected_execution

    scheduler = InProcessScheduler()
    trigger = ScheduledAnalysisTrigger(analysis, scheduler)

    trigger.schedule(inputs, run_at)

    scheduler.run_due(before_due)
    analysis.run.assert_not_called()

    scheduler.run_due(run_at)

    analysis.run.assert_called_once_with(inputs)
