from datetime import datetime, timezone
from unittest.mock import Mock

from app.application.analysis.daily_market_analysis import StockAnalysisInput
from app.application.execution.scheduled_trigger import ScheduledAnalysisTrigger
from app.domain.execution import Execution


def test_scheduled_trigger_registers_analysis_with_scheduler():
    inputs = [Mock(spec=StockAnalysisInput)]
    expected_execution = Execution.create()
    expected_execution.start()
    run_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    analysis = Mock()
    analysis.run.return_value.execution = expected_execution

    scheduler = Mock()
    trigger = ScheduledAnalysisTrigger(analysis, scheduler)

    result = trigger.schedule(inputs, run_at)

    assert result is None
    scheduler.schedule.assert_called_once()

    scheduled_operation = scheduler.schedule.call_args.args[0]
    scheduled_run_at = scheduler.schedule.call_args.args[1]

    assert scheduled_run_at == run_at
    assert scheduled_operation() is expected_execution
    analysis.run.assert_called_once_with(inputs)
