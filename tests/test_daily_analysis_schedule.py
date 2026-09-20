from datetime import datetime, timezone
from unittest.mock import Mock

from app.application.analysis.daily_market_analysis import StockAnalysisInput
from app.application.execution.daily_analysis_schedule import DailyAnalysisSchedule


def test_daily_analysis_schedule_registers_analysis_for_run_time():
    inputs = [Mock(spec=StockAnalysisInput)]
    run_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    trigger = Mock()
    schedule = DailyAnalysisSchedule(trigger)

    result = schedule.register(inputs, run_at)

    assert result is None
    trigger.schedule.assert_called_once_with(inputs, run_at)
