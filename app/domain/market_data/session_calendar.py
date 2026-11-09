from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class CalendarDayStatus(StrEnum):
    NON_TRADING = "NON_TRADING"
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class CalendarCoverageError(ValueError):
    """Raised when a requested date is outside the explicit calendar coverage."""


@dataclass(frozen=True)
class EGXCalendarDay:
    session_date: date
    status: CalendarDayStatus
    session_open: time | None = None
    session_close: time | None = None
    closed_at: datetime | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        is_trading = self.status in {
            CalendarDayStatus.SCHEDULED,
            CalendarDayStatus.OPEN,
            CalendarDayStatus.CLOSED,
        }
        if is_trading and (
            self.session_open is None or self.session_close is None
        ):
            raise ValueError("Trading calendar days require explicit open and close times")
        if not is_trading and (
            self.session_open is not None or self.session_close is not None
        ):
            raise ValueError("Non-trading and cancelled days cannot have session times")
        if (
            self.session_open is not None
            and self.session_close is not None
            and self.session_close <= self.session_open
        ):
            raise ValueError("Session close must be later than session open")
        if self.status is CalendarDayStatus.CLOSED:
            if self.closed_at is None:
                raise ValueError("A CLOSED session requires an explicit closed_at timestamp")
            if self.closed_at.tzinfo is None or self.closed_at.utcoffset() is None:
                raise ValueError("closed_at must be timezone-aware")
        elif self.closed_at is not None:
            raise ValueError("closed_at is only valid for a CLOSED session")
        if self.reason is not None and not self.reason.strip():
            raise ValueError("reason must be non-empty when provided")


@dataclass(frozen=True)
class EGXSessionCalendar:
    version: str
    timezone: str
    coverage_start: date
    coverage_end: date
    days: tuple[EGXCalendarDay, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("Calendar version is required")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Calendar timezone must be a valid IANA timezone") from error
        if self.timezone != "Africa/Cairo":
            raise ValueError("EGX session calendar timezone must be Africa/Cairo")
        if self.coverage_end < self.coverage_start:
            raise ValueError("Calendar coverage end must not precede coverage start")
        expected_dates = tuple(
            date.fromordinal(ordinal)
            for ordinal in range(
                self.coverage_start.toordinal(),
                self.coverage_end.toordinal() + 1,
            )
        )
        actual_dates = tuple(day.session_date for day in self.days)
        if actual_dates != expected_dates:
            raise ValueError(
                "Calendar must contain exactly one ordered explicit record for every "
                "date in its declared coverage"
            )

    def day_for(self, value: date) -> EGXCalendarDay:
        self._require_coverage(value, value)
        return self.days[(value - self.coverage_start).days]

    def is_completed_session(self, value: date, *, as_of: datetime) -> bool:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        day = self.day_for(value)
        if day.status is not CalendarDayStatus.CLOSED:
            return False
        assert day.closed_at is not None
        return day.closed_at <= as_of.astimezone(ZoneInfo(self.timezone))

    def completed_sessions_between(
        self,
        after_date: date,
        through_date: date,
        *,
        as_of: datetime,
    ) -> tuple[date, ...]:
        if through_date < after_date:
            raise ValueError("through_date must not precede after_date")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        self._require_coverage(after_date, through_date)
        return tuple(
            day.session_date
            for day in self.days
            if after_date < day.session_date <= through_date
            and day.status is CalendarDayStatus.CLOSED
            and day.closed_at is not None
            and day.closed_at <= as_of.astimezone(ZoneInfo(self.timezone))
        )

    def unconfirmed_trading_sessions_between(
        self, after_date: date, through_date: date
    ) -> tuple[date, ...]:
        if through_date < after_date:
            raise ValueError("through_date must not precede after_date")
        self._require_coverage(after_date, through_date)
        return tuple(
            day.session_date
            for day in self.days
            if after_date < day.session_date <= through_date
            and day.status in {
                CalendarDayStatus.SCHEDULED,
                CalendarDayStatus.OPEN,
            }
        )

    def _require_coverage(self, start: date, end: date) -> None:
        if start < self.coverage_start or end > self.coverage_end:
            raise CalendarCoverageError(
                f"Requested range {start.isoformat()}..{end.isoformat()} is outside "
                f"calendar coverage {self.coverage_start.isoformat()}.."
                f"{self.coverage_end.isoformat()}"
            )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EGXSessionCalendar:
        try:
            raw_days = payload["days"]
            days = tuple(
                EGXCalendarDay(
                    session_date=date.fromisoformat(item["date"]),
                    status=CalendarDayStatus(item["status"]),
                    session_open=(
                        time.fromisoformat(item["session_open"])
                        if item.get("session_open")
                        else None
                    ),
                    session_close=(
                        time.fromisoformat(item["session_close"])
                        if item.get("session_close")
                        else None
                    ),
                    closed_at=(
                        datetime.fromisoformat(item["closed_at"])
                        if item.get("closed_at")
                        else None
                    ),
                    reason=item.get("reason"),
                )
                for item in raw_days
            )
            return cls(
                version=payload["version"],
                timezone=payload["timezone"],
                coverage_start=date.fromisoformat(payload["coverage_start"]),
                coverage_end=date.fromisoformat(payload["coverage_end"]),
                days=days,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid EGX session calendar: {error}") from error
