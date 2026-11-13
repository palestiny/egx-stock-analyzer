from __future__ import annotations

from datetime import date

from app.application.market_data.session_calendar_store import SessionCalendarStore
from app.application.signals.validate_lifecycle_calendar_activation import (
    LifecycleEvaluationSchedule,
)
from app.domain.market_data.session_calendar import CalendarDayStatus


class CalendarBackedLifecycleEvaluationSchedule(LifecycleEvaluationSchedule):
    """Derive the next evaluation date from a trusted published calendar.

    On initial activation, use the candidate calendar. When a calendar is
    already active, preserve its next scheduled evaluation date and require
    the candidate to cover that date during validation. Missing schedule
    evidence fails closed; there is deliberately no fallback to the candidate.
    """

    def __init__(
        self,
        *,
        calendar_store: SessionCalendarStore,
        candidate_calendar_version: str,
    ) -> None:
        if (
            not isinstance(candidate_calendar_version, str)
            or not candidate_calendar_version.strip()
            or candidate_calendar_version != candidate_calendar_version.strip()
        ):
            raise ValueError("candidate_calendar_version must be normalized and non-empty")
        self._calendar_store = calendar_store
        self._candidate_calendar_version = candidate_calendar_version

    def next_evaluation_date(self, *, after: date) -> date | None:
        if not isinstance(after, date):
            raise ValueError("after must be a date")

        active = self._calendar_store.get_active()
        source = active
        if source is None:
            source = self._calendar_store.get_version(
                self._candidate_calendar_version
            )
        if source is None:
            return None

        return next(
            (
                day.session_date
                for day in source.calendar.days
                if day.session_date > after
                and day.status is CalendarDayStatus.SCHEDULED
            ),
            None,
        )
