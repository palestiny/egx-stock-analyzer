from datetime import datetime, time, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from app.application.execution.recurring_configured_market_analysis import (
    RecurringConfiguredMarketAnalysis,
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


def test_daily_recurrence_schedules_next_weekday_at_configured_local_time():
    clock = FakeClock(datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc))
    scheduler = FakeScheduler()
    capability = Mock()

    recurring = RecurringConfiguredMarketAnalysis(
        capability,
        scheduler,
        clock,
        schedule_time=time(21, 0),
    )

    recurring.start()

    assert scheduler.scheduled[0][0] == datetime(
        2026, 9, 18, 21, 0, tzinfo=CAIRO
    )


def test_recurrence_skips_weekend_when_calculating_next_occurrence():
    clock = FakeClock(datetime(2026, 9, 18, 22, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    recurring = RecurringConfiguredMarketAnalysis(
        Mock(),
        scheduler,
        clock,
        schedule_time=time(21, 0),
    )

    recurring.start()

    assert scheduler.scheduled[0][0] == datetime(
        2026, 9, 21, 21, 0, tzinfo=CAIRO
    )


def test_timezone_conversion_is_deterministic():
    clock = FakeClock(datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc))
    scheduler = FakeScheduler()
    recurring = RecurringConfiguredMarketAnalysis(
        Mock(),
        scheduler,
        clock,
        schedule_time=time(21, 0),
    )

    recurring.start()

    assert scheduler.scheduled[0][0].tzinfo == CAIRO
    assert scheduler.scheduled[0][0].hour == 21


def test_registration_does_not_execute_analysis_immediately():
    recurring = RecurringConfiguredMarketAnalysis(
        Mock(),
        FakeScheduler(),
        FakeClock(datetime(2026, 9, 18, 18, 0, tzinfo=CAIRO)),
        schedule_time=time(21, 0),
    )

    recurring.start()

    recurring._run_configured_market_analysis.execute.assert_not_called()


def test_due_occurrence_delegates_and_registers_next_occurrence():
    clock = FakeClock(datetime(2026, 9, 18, 20, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    capability = Mock()
    recurring = RecurringConfiguredMarketAnalysis(
        capability,
        scheduler,
        clock,
        schedule_time=time(21, 0),
    )

    recurring.start()
    clock.current = datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO)
    operation = scheduler.scheduled[0][1]
    operation()

    capability.execute.assert_called_once_with(clock.current.date())
    assert len(scheduler.scheduled) == 2
    assert scheduler.scheduled[1][0] == datetime(
        2026, 9, 21, 21, 0, tzinfo=CAIRO
    )


def test_missed_occurrence_is_skipped_and_next_future_occurrence_is_registered():
    clock = FakeClock(datetime(2026, 9, 18, 21, 5, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    capability = Mock()
    recurring = RecurringConfiguredMarketAnalysis(
        capability,
        scheduler,
        clock,
        schedule_time=time(21, 0),
    )

    recurring.start()
    operation = scheduler.scheduled[0][1]
    operation()

    capability.execute.assert_not_called()
    assert len(scheduler.scheduled) == 2
    assert scheduler.scheduled[1][0] == datetime(
        2026, 9, 21, 21, 0, tzinfo=CAIRO
    )


def test_same_occurrence_cannot_execute_twice():
    clock = FakeClock(datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    capability = Mock()
    recurring = RecurringConfiguredMarketAnalysis(
        capability,
        scheduler,
        clock,
        schedule_time=time(21, 0),
    )

    recurring.start()
    operation = scheduler.scheduled[0][1]
    operation()
    operation()

    capability.execute.assert_called_once()


def test_failed_occurrence_does_not_disable_future_recurrence():
    clock = FakeClock(datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    capability = Mock()
    capability.execute.side_effect = RuntimeError("analysis failed")
    recurring = RecurringConfiguredMarketAnalysis(
        capability,
        scheduler,
        clock,
        schedule_time=time(21, 0),
    )

    recurring.start()
    operation = scheduler.scheduled[0][1]

    with pytest.raises(RuntimeError, match="analysis failed"):
        operation()

    assert len(scheduler.scheduled) == 2
    assert scheduler.scheduled[1][0] == datetime(
        2026, 9, 21, 21, 0, tzinfo=CAIRO
    )


def test_overlapping_occurrence_is_not_started_concurrently():
    clock = FakeClock(datetime(2026, 9, 18, 21, 0, tzinfo=CAIRO))
    scheduler = FakeScheduler()
    capability = Mock()
    recurring = RecurringConfiguredMarketAnalysis(
        capability,
        scheduler,
        clock,
        schedule_time=time(21, 0),
    )

    recurring.start()
    operation = scheduler.scheduled[0][1]

    def execute(_as_of):
        operation()

    capability.execute.side_effect = execute
    operation()

    capability.execute.assert_called_once()


def test_naive_clock_is_rejected():
    recurring = RecurringConfiguredMarketAnalysis(
        Mock(),
        FakeScheduler(),
        FakeClock(datetime(2026, 9, 18, 18, 0)),
        schedule_time=time(21, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        recurring.start()
