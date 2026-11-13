from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Mapping, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from app.application.market_data.completed_daily_bar_source import ProviderDailyBarEvidence
from app.application.market_data.session_calendar_store import SessionCalendarStore
from app.application.signals.lifecycle_orchestrator import (
    SignalLifecycleOrchestrator,
    SignalLifecycleResult,
)
from app.application.signals.store import SignalHistoryStore
from app.domain.market_data.session_calendar import CalendarCoverageError
from app.domain.signals.lifecycle import CompletedDailyBarObservation
from app.domain.signals.model import SignalStatus


class DailyBarFinalityVerifier(Protocol):
    def verify_finality(self, evidence: ProviderDailyBarEvidence) -> bool: ...


@dataclass(frozen=True)
class OpportunitySessionEvaluation:
    status: str
    calendar_version: str | None
    processed_sessions: tuple[date, ...] = ()
    gap_session_date: date | None = None
    lifecycle_result: SignalLifecycleResult | None = None


class EvaluateOpportunityLifecycleSessions:
    """Chronologically reconcile every eligible session before advancing the cursor."""

    POLICY_VERSION = "dec139-completed-daily-bar-v1"
    POST_CLOSE_BUFFER = timedelta(minutes=60)
    EXPIRY_SESSIONS = 20

    def __init__(
        self,
        *,
        calendar_store: SessionCalendarStore,
        finality_verifier: DailyBarFinalityVerifier,
        history: SignalHistoryStore,
        lifecycle: SignalLifecycleOrchestrator,
    ) -> None:
        self._calendar_store = calendar_store
        self._finality_verifier = finality_verifier
        self._history = history
        self._lifecycle = lifecycle

    def execute(
        self,
        signal_id: UUID,
        *,
        through_date: date,
        bars_by_session: Mapping[date, ProviderDailyBarEvidence],
        evaluated_at: datetime,
    ) -> OpportunitySessionEvaluation:
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")

        active_signal = self._history.get(signal_id)
        if active_signal is None or active_signal.signal.status is not SignalStatus.ACTIVE:
            return OpportunitySessionEvaluation("NO_ACTIVE_OPPORTUNITY", None)

        history = self._history.history(signal_id)
        publications = [
            item for item in history
            if item.event in {"PUBLISHED", "PUBLISHED_VERSION"}
        ]
        if not publications:
            return OpportunitySessionEvaluation("OPPORTUNITY_NOT_PUBLISHED", None)
        publication = publications[0]

        active_calendar = self._calendar_store.get_active()
        if active_calendar is None:
            return OpportunitySessionEvaluation("NO_ACTIVE_EGX_SESSION_CALENDAR", None)

        calendar = active_calendar.calendar
        timezone = ZoneInfo(calendar.timezone)
        publication_date = publication.recorded_at.astimezone(timezone).date()

        has_newer_revision = any(
            (link := self._history.revision_link(record.signal_id)) is not None
            and link.parent_signal_id == signal_id
            for record in self._history.all_records()
        )
        if has_newer_revision:
            return OpportunitySessionEvaluation(
                "NOT_LATEST_OPPORTUNITY_REVISION", active_calendar.version
            )

        bootstrap = next(
            (
                record
                for record in self._lifecycle.bootstrap_records(signal_id)
                if record.calendar_version == active_calendar.version
            ),
            None,
        )
        if bootstrap is None:
            return OpportunitySessionEvaluation(
                "LIFECYCLE_BOOTSTRAP_REQUIRED", active_calendar.version
            )
        if (
            bootstrap.baseline_date != publication_date
            or bootstrap.publication_event != publication.event
            or bootstrap.publication_recorded_at != publication.recorded_at
        ):
            return OpportunitySessionEvaluation(
                "LIFECYCLE_BOOTSTRAP_PUBLICATION_MISMATCH", active_calendar.version
            )

        try:
            sessions = calendar.completed_sessions_between(
                publication_date,
                through_date,
                as_of=evaluated_at,
            )
        except CalendarCoverageError:
            return OpportunitySessionEvaluation(
                "SESSION_OUTSIDE_CALENDAR_COVERAGE", active_calendar.version
            )
        except ValueError:
            return OpportunitySessionEvaluation(
                "NO_NEW_COMPLETED_SESSIONS", active_calendar.version
            )

        if not sessions:
            return OpportunitySessionEvaluation(
                "NO_NEW_COMPLETED_SESSIONS", active_calendar.version
            )

        cursor = self._lifecycle.latest_completed_observation(signal_id)
        cursor_date = (
            cursor.bar.candle_at.astimezone(timezone).date()
            if cursor is not None
            else None
        )
        if cursor_date is not None and cursor_date > through_date:
            return OpportunitySessionEvaluation(
                "NO_NEW_COMPLETED_SESSIONS", active_calendar.version
            )
        if cursor_date is not None and cursor_date not in sessions:
            return OpportunitySessionEvaluation(
                "CURSOR_NOT_IN_ACTIVE_CALENDAR", active_calendar.version
            )

        processed: list[date] = []
        already_processed_count = (
            sum(1 for session in sessions if cursor_date is not None and session <= cursor_date)
        )
        last_result: SignalLifecycleResult | None = None

        if already_processed_count >= self.EXPIRY_SESSIONS:
            expired = self._lifecycle.expire_opportunity(
                signal_id,
                eligible_sessions=tuple(sessions[: self.EXPIRY_SESSIONS]),
                calendar_version=active_calendar.version,
                evaluated_at=evaluated_at,
            )
            return OpportunitySessionEvaluation(
                "EXPIRED" if expired is not None else "TERMINAL",
                active_calendar.version,
                lifecycle_result=expired,
            )

        for session_date in sessions:
            if cursor_date is not None and session_date <= cursor_date:
                continue

            evidence = bars_by_session.get(session_date)
            if evidence is None:
                self._lifecycle.mark_session_gap(
                    signal_id,
                    session_date=session_date,
                    calendar_version=active_calendar.version,
                    reason="MISSING_ELIGIBLE_BAR",
                    detected_at=evaluated_at,
                )
                return OpportunitySessionEvaluation(
                    "STALE_SESSION_DATA_GAP",
                    active_calendar.version,
                    tuple(processed),
                    session_date,
                    last_result,
                )

            if not isinstance(evidence, ProviderDailyBarEvidence):
                self._lifecycle.mark_session_gap(
                    signal_id,
                    session_date=session_date,
                    calendar_version=active_calendar.version,
                    reason="PROVIDER_EVIDENCE_REQUIRED",
                    detected_at=evaluated_at,
                )
                return OpportunitySessionEvaluation(
                    "PROVIDER_EVIDENCE_REQUIRED",
                    active_calendar.version,
                    tuple(processed),
                    session_date,
                    last_result,
                )

            bar = evidence.bar
            bar_session_date = bar.candle_at.astimezone(timezone).date()
            if evidence.session_date != session_date or bar_session_date != session_date:
                self._lifecycle.mark_session_gap(
                    signal_id,
                    session_date=session_date,
                    calendar_version=active_calendar.version,
                    reason="BAR_SESSION_DATE_MISMATCH",
                    detected_at=evaluated_at,
                )
                return OpportunitySessionEvaluation(
                    "BAR_SESSION_DATE_MISMATCH",
                    active_calendar.version,
                    tuple(processed),
                    session_date,
                    last_result,
                )
            if (
                bar.observed_at > evaluated_at
                or evidence.retrieved_at > evaluated_at
                or evidence.source_timestamp > evaluated_at
            ):
                self._lifecycle.mark_session_gap(
                    signal_id,
                    session_date=session_date,
                    calendar_version=active_calendar.version,
                    reason="OBSERVATION_FROM_FUTURE",
                    detected_at=evaluated_at,
                )
                return OpportunitySessionEvaluation(
                    "OBSERVATION_FROM_FUTURE",
                    active_calendar.version,
                    tuple(processed),
                    session_date,
                    last_result,
                )
            if not self._finality_verifier.verify_finality(evidence):
                self._lifecycle.mark_session_gap(
                    signal_id,
                    session_date=session_date,
                    calendar_version=active_calendar.version,
                    reason="PROVIDER_FINALITY_NOT_VERIFIED",
                    detected_at=evaluated_at,
                )
                return OpportunitySessionEvaluation(
                    "PROVIDER_FINALITY_NOT_VERIFIED",
                    active_calendar.version,
                    tuple(processed),
                    session_date,
                    last_result,
                )

            day = calendar.day_for(session_date)
            if day.session_close is None or day.closed_at is None:
                self._lifecycle.mark_session_gap(
                    signal_id,
                    session_date=session_date,
                    calendar_version=active_calendar.version,
                    reason="SESSION_CLOSE_EVIDENCE_INCOMPLETE",
                    detected_at=evaluated_at,
                )
                return OpportunitySessionEvaluation(
                    "SESSION_CLOSE_EVIDENCE_INCOMPLETE",
                    active_calendar.version,
                    tuple(processed),
                    session_date,
                    last_result,
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
                or evidence.retrieved_at.astimezone(timezone) < eligible_at
            ):
                return OpportunitySessionEvaluation(
                    "POST_CLOSE_BUFFER_NOT_ELAPSED",
                    active_calendar.version,
                    tuple(processed),
                    session_date,
                    last_result,
                )

            last_result = self._lifecycle.process_completed_daily_bar(
                signal_id,
                bar,
                policy_version=self.POLICY_VERSION,
                calendar_version=active_calendar.version,
                resolved_gap_session_date=session_date,
                resolved_gap_at=evaluated_at,
            )
            if last_result is None:
                return OpportunitySessionEvaluation(
                    "NO_ACTIVE_OPPORTUNITY",
                    active_calendar.version,
                    tuple(processed),
                    session_date,
                )
            processed.append(session_date)

            if last_result.signal.status is not SignalStatus.ACTIVE:
                return OpportunitySessionEvaluation(
                    "TERMINAL_TRANSITION",
                    active_calendar.version,
                    tuple(processed),
                    lifecycle_result=last_result,
                )

            total_processed = already_processed_count + len(processed)
            if total_processed >= self.EXPIRY_SESSIONS:
                eligible_sessions = tuple(sessions[: self.EXPIRY_SESSIONS])
                expired = self._lifecycle.expire_opportunity(
                    signal_id,
                    eligible_sessions=eligible_sessions,
                    calendar_version=active_calendar.version,
                    evaluated_at=evaluated_at,
                )
                return OpportunitySessionEvaluation(
                    "EXPIRED" if expired is not None else "TERMINAL",
                    active_calendar.version,
                    tuple(processed),
                    lifecycle_result=expired or last_result,
                )

        return OpportunitySessionEvaluation(
            "EVALUATED",
            active_calendar.version,
            tuple(processed),
            lifecycle_result=last_result,
        )
