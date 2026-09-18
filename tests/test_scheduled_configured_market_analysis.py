from datetime import date, datetime, timezone
from unittest.mock import Mock

from app.application.execution.scheduled_configured_market_analysis import (
    ScheduledConfiguredMarketAnalysis,
)
from app.domain.execution import Execution


RUN_AT = datetime(2026, 9, 19, 9, 30, tzinfo=timezone.utc)


def test_schedule_registers_one_operation_without_executing_it():
    expected_execution = Execution.create()
    expected_execution.start()
    expected_execution.complete()

    configured_analysis = Mock()
    configured_analysis.execute.return_value = expected_execution
    scheduler = Mock()

    trigger = ScheduledConfiguredMarketAnalysis(configured_analysis, scheduler)

    result = trigger.schedule(RUN_AT)

    assert result is None
    scheduler.schedule.assert_called_once()
    configured_analysis.execute.assert_not_called()

    scheduled_operation = scheduler.schedule.call_args.args[0]
    scheduled_run_at = scheduler.schedule.call_args.args[1]

    assert scheduled_run_at == RUN_AT
    assert scheduled_operation() is expected_execution
    configured_analysis.execute.assert_called_once_with(date.today())


def test_schedule_does_not_capture_the_universe_during_registration():
    configured_analysis = Mock()
    scheduler = Mock()

    trigger = ScheduledConfiguredMarketAnalysis(configured_analysis, scheduler)

    trigger.schedule(RUN_AT)

    configured_analysis.execute.assert_not_called()


def test_due_operation_propagates_configured_market_failure():
    configured_analysis = Mock()
    configured_analysis.execute.side_effect = RuntimeError("analysis unavailable")
    scheduler = Mock()

    trigger = ScheduledConfiguredMarketAnalysis(configured_analysis, scheduler)

    trigger.schedule(RUN_AT)
    scheduled_operation = scheduler.schedule.call_args.args[0]

    try:
        scheduled_operation()
    except RuntimeError as error:
        assert str(error) == "analysis unavailable"
    else:
        raise AssertionError("Expected scheduled operation failure to propagate")
