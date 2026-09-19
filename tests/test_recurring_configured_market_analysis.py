from datetime import datetime, time, timezone
from unittest.mock import ANY, Mock
from zoneinfo import ZoneInfo

import pytest

from app.application.execution.recurring_configured_market_analysis import (
    RecurringConfiguredMarketAnalysis,
)
from app.application.execution.run_configured_market_analysis_with_automatic_alert_delivery import (
    RunConfiguredMarketAnalysisWithAutomaticAlertDelivery,
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


def make_recurring(clock: FakeClock, scheduler: FakeScheduler, workflow=None):
    workflow = workflow or Mock(spec=RunConfiguredMarketAnalysisWithAutomaticAlertDelivery)
    return RecurringConfiguredMarketAnalysis(
        workflow,
        scheduler,
        clock,
        schedule_time=time(21, 0),
    ), workflow


def test_daily_recurrence_schedules_next_weekday_at_configured_local_time():
    clock = FakeClock(datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc))
    scheduler = FakeScheduler()
    recurring, _ = make_recurring(clock, scheduler)

    recurring.start()

    assert scheduler.scheduled[0][0] == datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO)


def test_recurrence_skips_weekend_when_calculating_next_occurrence():
    clock = FakeClock(datetime(2026, 9, 18, 22, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    recurring, _ = make_recurring(clock, scheduler)

    recurring.start()

    assert scheduler.scheduled[0][0] == datetime(2026, 9, 21, 21, 0, tzinfo=CAIRO)


def test_timezone_conversion_is_deterministic():
    clock = FakeClock(datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc))
    scheduler = FakeScheduler()
    recurring, _ = make_recurring(clock, scheduler)

    recurring.start()

    assert scheduler.scheduled[0][0].tzinfo == CAIRO
    assert scheduler.scheduled[0][0].hour == 21


def test_registration_does_not_execute_workflow_immediately():
    clock = FakeClock(datetime(2026, 9, 18, 18, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    recurring, workflow = make_recurring(clock, scheduler)

    recurring.start()

    workflow.execute.assert_not_called()


def test_due_occurrence_delegates_to_workflow_and_registers_next_occurrence():
    clock = FakeClock(datetime(2026, 9, 18, 20, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    recurring, workflow = make_recurring(clock, scheduler)

    recurring.start()
    clock.current = datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO)
    scheduler.scheduled[0][1]()

    workflow.execute.assert_called_once_with(ANY, clock.current.date())
    assert len(scheduler.scheduled) == 2


def test_missed_occurrence_is_skipped_and_next_future_occurrence_is_registered():
    clock = FakeClock(datetime(2026, 9, 18, 20, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    recurring, workflow = make_recurring(clock, scheduler)

    recurring.start()
    clock.current = datetime(2026, 9, 18, 21, 5, tzinfo=CAIRO)
    scheduler.scheduled[0][1]()

    workflow.execute.assert_not_called()
    assert len(scheduler.scheduled) == 2


def test_same_occurrence_cannot_execute_twice():
    clock = FakeClock(datetime(2026, 9, 18, 20, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    recurring, workflow = make_recurring(clock, scheduler)

    recurring.start()
    clock.current = datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO)
    operation = scheduler.scheduled[0][1]
    operation()
    operation()

    workflow.execute.assert_called_once_with(ANY, clock.current.date())


def test_failed_occurrence_does_not_disable_future_recurrence():
    clock = FakeClock(datetime(2026, 9, 18, 20, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    workflow = Mock(spec=RunConfiguredMarketAnalysisWithAutomaticAlertDelivery)
    workflow.execute.side_effect = RuntimeError("workflow failed")
    recurring, _ = make_recurring(clock, scheduler, workflow)

    recurring.start()
    clock.current = datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO)

    with pytest.raises(RuntimeError, match="workflow failed"):
        scheduler.scheduled[0][1]()

    assert len(scheduler.scheduled) == 2


def test_overlapping_occurrence_is_not_started_concurrently():
    clock = FakeClock(datetime(2026, 9, 18, 20, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    workflow = Mock(spec=RunConfiguredMarketAnalysisWithAutomaticAlertDelivery)
    recurring, _ = make_recurring(clock, scheduler, workflow)

    recurring.start()
    clock.current = datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO)

    def execute(_as_of):
        scheduler.scheduled[0][1]()

    workflow.execute.side_effect = execute
    scheduler.scheduled[0][1]()

    workflow.execute.assert_called_once()


def test_naive_clock_is_rejected():
    recurring, _ = make_recurring(
        FakeClock(datetime(2026, 9, 18, 18, 0)),
        FakeScheduler(),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        recurring.start()
