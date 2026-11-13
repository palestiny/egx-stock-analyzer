from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from app.application.market_data.session_calendar_store import SessionCalendarStore
from app.application.signals.lifecycle_unit_of_work import (
    LifecycleObservationRecord,
    SignalLifecycleTransaction,
    SignalLifecycleUnitOfWork,
)
from app.application.signals.store import SignalHistoryStore, SignalRecord
from app.domain.market_data.session_calendar import CalendarDayStatus
from app.domain.signals.model import SignalStatus


CAIRO = ZoneInfo("Africa/Cairo")
_PUBLICATION_EVENTS = frozenset({"PUBLISHED", "PUBLISHED_VERSION"})


class LifecycleEvaluationSchedule(Protocol):
    """Trusted schedule port; callers cannot submit the next session date."""

    def next_evaluation_date(self, *, after: date) -> date | None: ...


@dataclass(frozen=True)
class CalendarActivationBlocker:
    code: str
    signal_id: str | None
    detail: str


@dataclass(frozen=True)
class LifecycleCalendarActivationValidation:
    eligible: bool
    calendar_version: str
    next_evaluation_date: date | None
    checked_opportunity_count: int
    blockers: tuple[CalendarActivationBlocker, ...]


class ValidateLifecycleCalendarActivation:
    """Fail-closed precondition check for a candidate lifecycle calendar.

    This validator deliberately does not activate a calendar. The activation
    command/API must call it before changing the active pointer. A production
    schedule adapter is mandatory; no request-supplied date is accepted.
    """

    def __init__(
        self,
        *,
        history: SignalHistoryStore,
        calendar_store: SessionCalendarStore,
        unit_of_work: SignalLifecycleUnitOfWork,
        schedule: LifecycleEvaluationSchedule,
    ) -> None:
        self._history = history
        self._calendar_store = calendar_store
        self._unit_of_work = unit_of_work
        self._schedule = schedule

    def execute(
        self,
        *,
        calendar_version: str,
        as_of: datetime,
    ) -> LifecycleCalendarActivationValidation:
        if not isinstance(calendar_version, str) or not calendar_version.strip():
            raise ValueError("calendar_version is required")
        if calendar_version != calendar_version.strip():
            raise ValueError("calendar_version must be normalized")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        after_date = as_of.astimezone(CAIRO).date()
        next_date = self._schedule.next_evaluation_date(after=after_date)
        blockers: list[CalendarActivationBlocker] = []
        if next_date is None:
            blockers.append(CalendarActivationBlocker(
                "NEXT_EVALUATION_DATE_UNAVAILABLE", None,
                "trusted schedule did not provide the next lifecycle evaluation date",
            ))
        elif not isinstance(next_date, date) or isinstance(next_date, datetime):
            raise ValueError("trusted schedule must return a date or None")
        elif next_date <= after_date:
            blockers.append(CalendarActivationBlocker(
                "NEXT_EVALUATION_DATE_NOT_FUTURE", None,
                "trusted schedule must return a session date strictly after the current Cairo date",
            ))

        stored = self._calendar_store.get_version(calendar_version)
        if stored is None:
            blockers.append(CalendarActivationBlocker(
                "CALENDAR_VERSION_NOT_PUBLISHED", None,
                "candidate calendar version is not durably published",
            ))
            return LifecycleCalendarActivationValidation(
                False, calendar_version, next_date, 0, tuple(blockers)
            )

        calendar = stored.calendar
        if (
            stored.version != calendar_version
            or calendar.version != calendar_version
            or calendar.timezone != "Africa/Cairo"
            or len(stored.sha256) != 64
            or any(c not in "0123456789abcdef" for c in stored.sha256.lower())
            or not stored.published_by.strip()
            or not stored.source_reference.strip()
            or not stored.publication_reason.strip()
            or stored.published_at.tzinfo is None
            or stored.published_at.utcoffset() is None
        ):
            blockers.append(CalendarActivationBlocker(
                "CALENDAR_PUBLICATION_EVIDENCE_INVALID", None,
                "candidate calendar identity, digest, timezone, or publication metadata is invalid",
            ))
            return LifecycleCalendarActivationValidation(
                False, calendar_version, next_date, 0, tuple(blockers)
            )

        all_records = self._history.all_records()
        signal_ids = {record.signal_id for record in all_records}
        parent_ids = {
            link.parent_signal_id
            for signal_id in signal_ids
            if (link := self._history.revision_link(signal_id)) is not None
        }
        active: list[SignalRecord] = []
        for signal_id in sorted(signal_ids - parent_ids, key=str):
            latest = self._history.get(signal_id)
            if latest is not None and latest.signal.status is SignalStatus.ACTIVE:
                active.append(latest)

        bootstrap_by_signal = self._unit_of_work.execute(
            lambda tx: {
                signal_id: tx.bootstrap_records(signal_id)
                for signal_id in signal_ids
            }
        )
        batches = self._unit_of_work.execute(lambda tx: tx.bootstrap_batches())
        batch_by_id = {item.batch_id: item for item in batches}
        actual_batch_counts: dict[object, int] = {}
        for records in bootstrap_by_signal.values():
            for record in records:
                actual_batch_counts[record.batch_id] = actual_batch_counts.get(record.batch_id, 0) + 1

        for latest in active:
            signal_id = latest.signal_id
            sid = str(signal_id)
            publication = next(
                (
                    item for item in self._history.history(signal_id)
                    if item.event in _PUBLICATION_EVENTS
                ),
                None,
            )
            if publication is None:
                blockers.append(CalendarActivationBlocker(
                    "PUBLICATION_PROVENANCE_MISSING", sid,
                    "active opportunity has no immutable PUBLISHED/PUBLISHED_VERSION event",
                ))
                continue
            if publication.recorded_at.tzinfo is None or publication.recorded_at.utcoffset() is None:
                blockers.append(CalendarActivationBlocker(
                    "PUBLICATION_TIMESTAMP_INVALID", sid,
                    "publication timestamp is not timezone-aware",
                ))
                continue
            baseline = publication.recorded_at.astimezone(CAIRO).date()
            matching = tuple(
                item for item in bootstrap_by_signal.get(signal_id, ())
                if item.calendar_version == calendar_version
            )
            if len(matching) != 1:
                blockers.append(CalendarActivationBlocker(
                    "BOOTSTRAP_MISSING_OR_AMBIGUOUS", sid,
                    "exactly one publication baseline for this opportunity and candidate calendar is required",
                ))
                continue
            bootstrap = matching[0]
            batch = batch_by_id.get(bootstrap.batch_id)
            if (
                bootstrap.baseline_date != baseline
                or bootstrap.publication_event != publication.event
                or bootstrap.publication_recorded_at != publication.recorded_at
                or bootstrap.calendar_version != calendar_version
                or not bootstrap.operator_id.strip()
                or not bootstrap.reason.strip()
                or batch is None
                or batch.calendar_version != calendar_version
                or batch.operator_id != bootstrap.operator_id
                or batch.reason != bootstrap.reason
                or batch.opportunity_count != actual_batch_counts.get(bootstrap.batch_id, 0)
                or len(batch.batch_digest) != 64
                or any(c not in "0123456789abcdef" for c in batch.batch_digest.lower())
            ):
                blockers.append(CalendarActivationBlocker(
                    "BOOTSTRAP_BATCH_INCOMPLETE_OR_CONFLICTED", sid,
                    "bootstrap provenance or complete append-only batch audit does not match",
                ))
                continue

            if next_date is None:
                continue
            if next_date < baseline:
                blockers.append(CalendarActivationBlocker(
                    "NEXT_EVALUATION_PRECEDES_BASELINE", sid,
                    "trusted next evaluation date precedes the publication baseline",
                ))
                continue
            if baseline < calendar.coverage_start or next_date > calendar.coverage_end:
                blockers.append(CalendarActivationBlocker(
                    "CALENDAR_COVERAGE_INCOMPLETE", sid,
                    f"candidate calendar does not cover {baseline.isoformat()}..{next_date.isoformat()}",
                ))
                continue

            try:
                for ordinal in range(baseline.toordinal(), next_date.toordinal() + 1):
                    calendar.day_for(date.fromordinal(ordinal))
                next_day = calendar.day_for(next_date)
            except ValueError as error:
                blockers.append(CalendarActivationBlocker(
                    "CALENDAR_DATE_GAP", sid, str(error)
                ))
                continue
            if next_day.status is not CalendarDayStatus.SCHEDULED:
                blockers.append(CalendarActivationBlocker(
                    "NEXT_EVALUATION_NOT_SCHEDULED", sid,
                    "a future lifecycle evaluation date must be explicitly SCHEDULED in the candidate calendar",
                ))
                continue

            def read_latest_cursor(
                transaction: SignalLifecycleTransaction,
            ) -> LifecycleObservationRecord | None:
                return transaction.latest_observation(signal_id)

            cursor = self._unit_of_work.execute(read_latest_cursor)
            if cursor is not None:
                cursor_date = cursor.bar.candle_at.astimezone(CAIRO).date()
                if cursor_date <= baseline:
                    blockers.append(CalendarActivationBlocker(
                        "RECONCILED_CURSOR_NOT_AFTER_BASELINE", sid,
                        "latest reconciled session must be strictly after publication baseline",
                    ))
                    continue
                if cursor_date >= next_date:
                    blockers.append(CalendarActivationBlocker(
                        "NEXT_EVALUATION_NOT_AFTER_CURSOR", sid,
                        "trusted next evaluation date must be later than the latest reconciled session",
                    ))
                    continue
                try:
                    cursor_day = calendar.day_for(cursor_date)
                except ValueError as error:
                    blockers.append(CalendarActivationBlocker(
                        "RECONCILED_CURSOR_OUTSIDE_CALENDAR", sid, str(error)
                    ))
                    continue
                if cursor_day.status is not CalendarDayStatus.CLOSED:
                    blockers.append(CalendarActivationBlocker(
                        "RECONCILED_CURSOR_NOT_CLOSED_IN_CANDIDATE", sid,
                        "candidate calendar must explicitly confirm the latest reconciled session as CLOSED",
                    ))

        return LifecycleCalendarActivationValidation(
            eligible=not blockers,
            calendar_version=calendar_version,
            next_evaluation_date=next_date,
            checked_opportunity_count=len(active),
            blockers=tuple(blockers),
        )
