from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.application.analysis.run_configured_market_analysis_with_automatic_alerts import (
    RunConfiguredMarketAnalysisWithAutomaticAlerts,
)
from app.application.execution.scheduler import Scheduler


CAIRO_TIMEZONE = ZoneInfo("Africa/Cairo")


class Clock(Protocol):
    def now(self) -> datetime:
        ...


@dataclass(frozen=True)
class OccurrenceIdentity:
    schedule_id: UUID
    scheduled_date: date
    scheduled_time: time


class RecurringConfiguredMarketAnalysis:
    """Own recurring market-analysis policy while delegating timing to Scheduler."""

    def __init__(
        self,
        run_configured_market_analysis: RunConfiguredMarketAnalysis,
        scheduler: Scheduler,
        clock: Clock,
        schedule_time: time,
        timezone: ZoneInfo = CAIRO_TIMEZONE,
    ) -> None:
        self._run_configured_market_analysis = run_configured_market_analysis
        self._scheduler = scheduler
        self._clock = clock
        self._schedule_time = schedule_time.replace(tzinfo=None)
        self._timezone = timezone
        self._schedule_id = uuid4()
        self._consumed_occurrences: set[OccurrenceIdentity] = set()
        self._running = False
        self._started = False

    def start(self) -> None:
        if self._started:
            raise ValueError("Recurring market analysis is already started")

        self._started = True
        now = self._local_now()
        self._schedule_occurrence(self._next_occurrence(now))

    def _local_now(self) -> datetime:
        now = self._clock.now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Clock must return a timezone-aware datetime")
        return now.astimezone(self._timezone)

    def _next_occurrence(self, now: datetime) -> datetime:
        candidate = now.replace(
            hour=self._schedule_time.hour,
            minute=self._schedule_time.minute,
            second=self._schedule_time.second,
            microsecond=self._schedule_time.microsecond,
        )

        if candidate <= now:
            candidate += timedelta(days=1)

        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

        return candidate

    def _schedule_occurrence(self, occurrence: datetime) -> None:
        identity = OccurrenceIdentity(
            schedule_id=self._schedule_id,
            scheduled_date=occurrence.date(),
            scheduled_time=self._schedule_time,
        )

        def operation() -> None:
            self._run_occurrence(identity, occurrence)

        self._scheduler.schedule(operation, occurrence)

    def _run_occurrence(
        self,
        identity: OccurrenceIdentity,
        occurrence: datetime,
    ) -> None:
        if identity in self._consumed_occurrences:
            return

        now = self._local_now()
        if now < occurrence:
            return

        self._consumed_occurrences.add(identity)

        if now > occurrence:
            self._schedule_occurrence(self._next_occurrence(now))
            return

        if self._running:
            self._schedule_occurrence(self._next_occurrence(now))
            return

        self._running = True
        try:
            self._run_configured_market_analysis.execute(occurrence.date())
        finally:
            self._running = False
            self._schedule_occurrence(self._next_occurrence(occurrence + timedelta(seconds=1)))
