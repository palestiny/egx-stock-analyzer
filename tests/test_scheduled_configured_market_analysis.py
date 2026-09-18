from datetime import date, datetime
from unittest.mock import Mock, patch

from app.application.execution.scheduler import InProcessScheduler

from app.application.execution.scheduled_configured_market_analysis import ScheduledConfiguredMarketAnalysis


def test_schedule_registers_one_operation_without_running_it():
    scheduler = Mock()
    capability = Mock()
    trigger = ScheduledConfiguredMarketAnalysis(capability, scheduler)
    run_at = datetime(2026, 9, 18, 22, 0)

    trigger.schedule(run_at)

    scheduler.schedule.assert_called_once()
    assert scheduler.schedule.call_args.args[1] == run_at
    capability.execute.assert_not_called()


def test_due_operation_uses_date_at_execution_time():
    scheduler = Mock()
    capability = Mock()
    trigger = ScheduledConfiguredMarketAnalysis(capability, scheduler)

    trigger.schedule(datetime(2026, 9, 18, 22, 0))
    operation = scheduler.schedule.call_args.args[0]

    with patch("app.application.execution.scheduled_configured_market_analysis.date") as mocked_date:
        mocked_date.today.return_value = date(2026, 9, 19)
        operation()

    capability.execute.assert_called_once_with(date(2026, 9, 19))


def test_registration_does_not_execute_capability():
    scheduler = Mock()
    capability = Mock()
    trigger = ScheduledConfiguredMarketAnalysis(capability, scheduler)

    trigger.schedule(datetime(2026, 9, 18, 22, 0))

    capability.execute.assert_not_called()



def test_due_operation_is_removed_by_existing_scheduler():
    scheduler = InProcessScheduler()
    capability = Mock()
    trigger = ScheduledConfiguredMarketAnalysis(capability, scheduler)

    trigger.schedule(datetime(2026, 9, 18, 22, 0))

    scheduler.run_due(datetime(2026, 9, 18, 22, 1))

    assert scheduler.pending_count() == 0
    capability.execute.assert_called_once_with(date(2026, 9, 18))
