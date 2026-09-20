from datetime import datetime, timezone
from unittest.mock import Mock

from app.application.analysis.daily_market_analysis import StockAnalysisInput
from app.application.execution.daily_analysis_schedule import DailyAnalysisSchedule
from app.application.execution.scheduled_trigger import ScheduledAnalysisTrigger
from app.application.execution.scheduler import InProcessScheduler
from app.domain.execution import Execution


def test_daily_analysis_schedule_runs_analysis_when_due():
    inputs = [Mock(spec=StockAnalysisInput)]
    run_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    expected_execution = Execution.create()
    expected_execution.start()

    analysis = Mock()
    analysis.run.return_value.execution = expected_execution

    scheduler = InProcessScheduler()
    trigger = ScheduledAnalysisTrigger(analysis, scheduler)
    schedule = DailyAnalysisSchedule(trigger)

    schedule.register(inputs, run_at)

    analysis.run.assert_not_called()
    assert scheduler.pending_count() == 1

    scheduler.run_due(run_at)

    analysis.run.assert_called_once_with(inputs)
    assert scheduler.pending_count() == 0
