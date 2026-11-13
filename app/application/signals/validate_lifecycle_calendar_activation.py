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
from app.domain.market_data.calendar_evidence import (
    CalendarEvidence,
    CalendarEvidenceKind,
    CalendarEvidenceSourceClass,
)
from app.domain.market_data.session_calendar import CalendarDayStatus
from app.domain.signals.model import SignalStatus


CAIRO = ZoneInfo("Africa/Cairo")
_PUBLICATION_EVENTS = frozenset({"PUBLISHED", "PUBLISHED_VERSION"})


class CalendarActivationEvidenceStore(Protocol):
    """Returns hash-verified evidence explicitly linked to a calendar day."""

    def list_for_calendar_day(
        self, calendar_version: str, session_date: date
    ) -> tuple[CalendarEvidence, ...]: ...


class CalendarEvidenceAuthenticityGate(Protocol):
    """Revalidates an evidence item's publisher origin and exact artifact bytes."""

    def revalidate_for_activation(self, evidence: CalendarEvidence, *, at: datetime) -> object: ...

    def assert_preflight_verification(self, evidence: CalendarEvidence, *, at: datetime) -> object: ...


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

    This validator never mutates the active pointer. The atomic SQLite
    coordinator supplies a caller-owned lifecycle transaction so bootstrap
    and cursor reads are serialized with the subsequent pointer and audit
    writes. A trusted schedule adapter is mandatory; no request-supplied date
    is accepted.
    """

    def __init__(
        self,
        *,
        history: SignalHistoryStore,
        calendar_store: SessionCalendarStore,
        unit_of_work: SignalLifecycleUnitOfWork,
        schedule: LifecycleEvaluationSchedule,
        evidence_store: CalendarActivationEvidenceStore,
        authenticity_verifier: CalendarEvidenceAuthenticityGate | None = None,
    ) -> None:
        self._history = history
        self._calendar_store = calendar_store
        self._unit_of_work = unit_of_work
        self._schedule = schedule
        self._evidence_store = evidence_store
        self._authenticity_verifier = authenticity_verifier

    def preflight_source_authenticity(
        self,
        calendar_version: str,
        *,
        at: datetime,
    ) -> tuple[CalendarActivationBlocker, ...]:
        """Perform network re-fetch before the coordinator opens its write transaction."""
        stored = self._calendar_store.get_version(calendar_version)
        if stored is None:
            return ()
        blockers: list[CalendarActivationBlocker] = []
        for day in stored.calendar.days:
            linked = self._evidence_store.list_for_calendar_day(
                calendar_version, day.session_date
            )
            superseded_ids = {
                item.supersedes_evidence_id
                for item in linked
                if item.supersedes_evidence_id is not None
            }
            for item in linked:
                if item.evidence_id in superseded_ids or item.source_class not in {
                    CalendarEvidenceSourceClass.A,
                    CalendarEvidenceSourceClass.A_R,
                }:
                    continue
                if self._authenticity_verifier is None:
                    blockers.append(CalendarActivationBlocker(
                        "CALENDAR_SOURCE_AUTHENTICITY_VERIFIER_NOT_CONFIGURED",
                        None,
                        f"{day.session_date.isoformat()} has primary evidence but no source-authenticity verifier is configured",
                    ))
                    continue
                try:
                    self._authenticity_verifier.revalidate_for_activation(item, at=at)
                except Exception as error:
                    blockers.append(CalendarActivationBlocker(
                        "CALENDAR_SOURCE_AUTHENTICITY_UNVERIFIED",
                        None,
                        f"{day.session_date.isoformat()} evidence {item.evidence_id} failed source-authenticity preflight: {error}",
                    ))
        return tuple(blockers)

    def execute(
        self,
        *,
        calendar_version: str,
        as_of: datetime,
        transaction: SignalLifecycleTransaction | None = None,
    ) -> LifecycleCalendarActivationValidation:
        if not isinstance(calendar_version, str) or not calendar_version.strip():
            raise ValueError("calendar_version is required")
        if calendar_version != calendar_version.strip():
            raise ValueError("calendar_version must be normalized")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        preflight_blockers = (
            self.preflight_source_authenticity(calendar_version, at=as_of)
            if transaction is None else ()
        )
        after_date = as_of.astimezone(CAIRO).date()
        next_date = self._schedule.next_evaluation_date(after=after_date)
        blockers: list[CalendarActivationBlocker] = list(preflight_blockers)
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
        for day in calendar.days:
            required_kinds = {
                CalendarDayStatus.NON_TRADING: {CalendarEvidenceKind.CLOSURE},
                CalendarDayStatus.CANCELLED: {CalendarEvidenceKind.CANCELLATION},
                CalendarDayStatus.SCHEDULED: {CalendarEvidenceKind.SCHEDULE},
                CalendarDayStatus.OPEN: {
                    CalendarEvidenceKind.SCHEDULE,
                    CalendarEvidenceKind.OPEN_CONFIRMATION,
                },
                CalendarDayStatus.CLOSED: {
                    CalendarEvidenceKind.SCHEDULE,
                    CalendarEvidenceKind.CLOSE_CONFIRMATION,
                },
            }[day.status]
            if day.exceptional_hours:
                required_kinds = required_kinds | {CalendarEvidenceKind.EXCEPTIONAL_HOURS}
            linked_evidence = self._evidence_store.list_for_calendar_day(
                calendar_version, day.session_date
            )
            superseded_ids = {
                item.supersedes_evidence_id
                for item in linked_evidence
                if item.supersedes_evidence_id is not None
            }
            current_evidence = tuple(
                item for item in linked_evidence
                if item.evidence_id not in superseded_ids
            )
            for item in current_evidence:
                if item.source_class in {
                    CalendarEvidenceSourceClass.A,
                    CalendarEvidenceSourceClass.A_R,
                }:
                    if self._authenticity_verifier is None:
                        blockers.append(CalendarActivationBlocker(
                            "CALENDAR_SOURCE_AUTHENTICITY_VERIFIER_NOT_CONFIGURED",
                            None,
                            f"{day.session_date.isoformat()} has primary evidence but no source-authenticity verifier is configured",
                        ))
                        continue
                    try:
                        self._authenticity_verifier.assert_preflight_verification(
                            item, at=as_of
                        )
                    except Exception as error:
                        blockers.append(CalendarActivationBlocker(
                            "CALENDAR_SOURCE_AUTHENTICITY_UNVERIFIED",
                            None,
                            f"{day.session_date.isoformat()} evidence {item.evidence_id} failed independent source verification: {error}",
                        ))
            for kind in required_kinds:
                kind_evidence = tuple(
                    item for item in current_evidence if item.evidence_kind is kind
                )
                if not kind_evidence:
                    blockers.append(CalendarActivationBlocker(
                        "CALENDAR_DAY_EVIDENCE_MISSING", None,
                        f"{day.session_date.isoformat()} lacks linked {kind.value} evidence",
                    ))
                    continue
                if len({item.claim for item in kind_evidence}) > 1:
                    blockers.append(CalendarActivationBlocker(
                        "CALENDAR_DAY_EVIDENCE_CONFLICT", None,
                        f"{day.session_date.isoformat()} has conflicting unsuperseded {kind.value} claims",
                    ))
                if not any(
                    item.source_class is CalendarEvidenceSourceClass.A
                    and item.source_publisher == "EGX"
                    and item.market_scope == "EGX_MARKET_WIDE"
                    and item.effective_from is not None
                    and item.effective_through is not None
                    and item.effective_from <= day.session_date <= item.effective_through
                    for item in kind_evidence
                ):
                    blockers.append(CalendarActivationBlocker(
                        "CALENDAR_DAY_PRIMARY_EVIDENCE_MISSING", None,
                        f"{day.session_date.isoformat()} lacks Class A EGX-wide primary {kind.value} evidence",
                    ))
            if (
                CalendarEvidenceKind.EXCEPTIONAL_HOURS in {
                    item.evidence_kind for item in current_evidence
                }
                and not day.exceptional_hours
            ):
                blockers.append(CalendarActivationBlocker(
                    "CALENDAR_EXCEPTIONAL_HOURS_EVIDENCE_INVALID", None,
                    f"{day.session_date.isoformat()} has exceptional-hours evidence without an explicit calendar marker",
                ))
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

        def read_bootstrap_records(tx: SignalLifecycleTransaction):
            return {
                signal_id: tx.bootstrap_records(signal_id)
                for signal_id in signal_ids
            }

        def read_bootstrap_batches(tx: SignalLifecycleTransaction):
            return tx.bootstrap_batches()

        if transaction is None:
            bootstrap_by_signal = self._unit_of_work.execute(read_bootstrap_records)
            batches = self._unit_of_work.execute(read_bootstrap_batches)
        else:
            bootstrap_by_signal = read_bootstrap_records(transaction)
            batches = read_bootstrap_batches(transaction)
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

            cursor = (
                self._unit_of_work.execute(read_latest_cursor)
                if transaction is None
                else read_latest_cursor(transaction)
            )
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
