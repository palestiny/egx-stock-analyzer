from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
from datetime import datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from app.application.market_data.session_calendar_store import SessionCalendarStore
from app.application.signals.lifecycle_orchestrator import (
    SignalLifecycleOrchestrator,
    SignalLifecycleResult,
)
from app.domain.market_data.session_calendar import CalendarDayStatus, CalendarCoverageError
from app.domain.signals.lifecycle import CompletedDailyBarObservation


class DailyBarFinalityVerifier(Protocol):
    def verify_finality(self, bar: CompletedDailyBarObservation) -> bool: ...


@dataclass(frozen=True)
class CompletedDailyBarEvaluation:
    accepted: bool
    reason: str
    calendar_version: str | None
    lifecycle_result: SignalLifecycleResult | None = None


class EvaluateCompletedDailyBar:
    """Fail-closed application boundary for one completed EGX daily candle."""

    POLICY_VERSION = "dec139-completed-daily-bar-v1"
    POST_CLOSE_BUFFER = timedelta(minutes=60)

    def __init__(
        self,
        *,
        calendar_store: SessionCalendarStore,
        finality_verifier: DailyBarFinalityVerifier,
        lifecycle: SignalLifecycleOrchestrator,
    ) -> None:
        self._calendar_store = calendar_store
        self._finality_verifier = finality_verifier
        self._lifecycle = lifecycle

    def execute(
        self,
        signal_id: UUID,
        bar: CompletedDailyBarObservation,
        *,
        evaluated_at: datetime,
    ) -> CompletedDailyBarEvaluation:
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        active = self._calendar_store.get_active()
        if active is None:
            return CompletedDailyBarEvaluation(
                False, "NO_ACTIVE_EGX_SESSION_CALENDAR", None
            )

        calendar = active.calendar
        timezone = ZoneInfo(calendar.timezone)
        session_date = bar.candle_at.astimezone(timezone).date()
        try:
            day = calendar.day_for(session_date)
        except CalendarCoverageError:
            return CompletedDailyBarEvaluation(
                False, "SESSION_OUTSIDE_CALENDAR_COVERAGE", active.version
            )

        if day.status is not CalendarDayStatus.CLOSED:
            return CompletedDailyBarEvaluation(
                False, "SESSION_NOT_EXPLICITLY_CLOSED", active.version
            )
        if not calendar.is_completed_session(session_date, as_of=evaluated_at):
            return CompletedDailyBarEvaluation(
                False, "SESSION_CLOSE_NOT_CONFIRMED", active.version
            )
        if day.session_close is None or day.closed_at is None:
            return CompletedDailyBarEvaluation(
                False, "SESSION_CLOSE_EVIDENCE_INCOMPLETE", active.version
            )

        configured_close = datetime.combine(
            session_date, day.session_close, tzinfo=timezone
        )
        eligible_at = max(
            configured_close + self.POST_CLOSE_BUFFER,
            day.closed_at.astimezone(timezone),
        )
        if (
            evaluated_at.astimezone(timezone) < eligible_at
            or bar.observed_at.astimezone(timezone) < eligible_at
        ):
            return CompletedDailyBarEvaluation(
                False, "POST_CLOSE_BUFFER_NOT_ELAPSED", active.version
            )

        if bar.observed_at > evaluated_at:
            return CompletedDailyBarEvaluation(
                False, "OBSERVATION_FROM_FUTURE", active.version
            )

        if not self._finality_verifier.verify_finality(bar):
            return CompletedDailyBarEvaluation(
                False, "PROVIDER_FINALITY_NOT_VERIFIED", active.version
            )

        result = self._lifecycle.process_completed_daily_bar(
            signal_id,
            bar,
            policy_version=self.POLICY_VERSION,
            calendar_version=active.version,
        )
        if result is None:
            return CompletedDailyBarEvaluation(
                False, "NO_PUBLISHED_ACTIVE_OPPORTUNITY", active.version
            )
        return CompletedDailyBarEvaluation(
            True, "EVALUATED", active.version, result
        )
