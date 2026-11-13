from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from app.application.market_data.session_calendar_store import SessionCalendarStore
from app.application.signals.lifecycle_unit_of_work import (
    LifecycleBootstrapBatchRecord,
    LifecycleBootstrapRecord,
    SignalLifecycleUnitOfWork,
)
from app.application.signals.store import SignalHistoryStore, SignalRecord
from app.domain.market_data.session_calendar import CalendarDayStatus
from app.domain.signals.model import SignalStatus


CAIRO = ZoneInfo("Africa/Cairo")


@dataclass(frozen=True)
class LifecycleBootstrapResult:
    status: str
    batch_id: str | None
    calendar_version: str
    opportunity_count: int
    batch_digest: str | None


class BootstrapOpportunityLifecycle:
    """Create immutable publication baselines for every active latest revision."""

    PUBLICATION_EVENTS = frozenset({"PUBLISHED", "PUBLISHED_VERSION"})

    def __init__(
        self,
        *,
        history: SignalHistoryStore,
        calendar_store: SessionCalendarStore,
        unit_of_work: SignalLifecycleUnitOfWork,
    ) -> None:
        self._history = history
        self._calendar_store = calendar_store
        self._unit_of_work = unit_of_work

    def execute(
        self,
        *,
        calendar_version: str,
        operator_id: str,
        reason: str,
        next_evaluation_date: date,
        recorded_at: datetime,
    ) -> LifecycleBootstrapResult:
        if not calendar_version.strip() or calendar_version != calendar_version.strip():
            raise ValueError("calendar_version is required and must be normalized")
        if not operator_id.strip():
            raise ValueError("authenticated operator identity is required")
        operator_id = operator_id.strip()
        if not reason.strip():
            raise ValueError("bootstrap reason is required")
        if not isinstance(next_evaluation_date, date) or isinstance(next_evaluation_date, datetime):
            raise ValueError("next_evaluation_date must be a date")
        if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")

        stored_calendar = self._calendar_store.get_version(calendar_version)
        if stored_calendar is None:
            raise ValueError("candidate calendar version is not published")
        calendar = stored_calendar.calendar
        if calendar.version != calendar_version or calendar.timezone != "Africa/Cairo":
            raise ValueError("candidate calendar identity or timezone is invalid")
        if (
            len(stored_calendar.sha256) != 64
            or any(character not in "0123456789abcdef" for character in stored_calendar.sha256.lower())
            or not stored_calendar.published_by.strip()
            or not stored_calendar.source_reference.strip()
            or not stored_calendar.publication_reason.strip()
            or stored_calendar.published_at.tzinfo is None
            or stored_calendar.published_at.utcoffset() is None
        ):
            raise ValueError("candidate calendar publication evidence is incomplete")

        all_records = self._history.all_records()
        signal_ids = {record.signal_id for record in all_records}
        child_signal_ids = {
            link.parent_signal_id
            for signal_id in signal_ids
            if (link := self._history.revision_link(signal_id)) is not None
        }

        candidates: list[tuple[SignalRecord, SignalRecord, date]] = []
        for signal_id in sorted(signal_ids - child_signal_ids, key=str):
            latest = self._history.get(signal_id)
            if latest is None or latest.signal.status is not SignalStatus.ACTIVE:
                continue
            publication = next(
                (
                    item
                    for item in self._history.history(signal_id)
                    if item.event in self.PUBLICATION_EVENTS
                ),
                None,
            )
            if publication is None:
                continue
            baseline_date = publication.recorded_at.astimezone(CAIRO).date()
            if next_evaluation_date < baseline_date:
                raise ValueError("next evaluation date precedes publication baseline")
            if (
                baseline_date < calendar.coverage_start
                or next_evaluation_date > calendar.coverage_end
            ):
                raise ValueError(
                    f"calendar {calendar_version} does not explicitly cover "
                    f"{baseline_date.isoformat()}..{next_evaluation_date.isoformat()}"
                )
            for ordinal in range(baseline_date.toordinal(), next_evaluation_date.toordinal() + 1):
                calendar.day_for(date.fromordinal(ordinal))
            next_day = calendar.day_for(next_evaluation_date)
            if next_day.status not in {
                CalendarDayStatus.SCHEDULED,
                CalendarDayStatus.OPEN,
                CalendarDayStatus.CLOSED,
            }:
                raise ValueError("next evaluation date is not a scheduled EGX session")
            candidates.append((latest, publication, baseline_date))

        existing_by_signal = self._unit_of_work.execute(
            lambda transaction: {
                signal_id: transaction.bootstrap_records(signal_id)
                for signal_id in signal_ids
            }
        )

        pending: list[tuple[SignalRecord, SignalRecord, date]] = []
        for latest, publication, baseline_date in candidates:
            existing = next(
                (
                    item
                    for item in existing_by_signal.get(latest.signal_id, ())
                    if item.calendar_version == calendar_version
                ),
                None,
            )
            if existing is None:
                pending.append((latest, publication, baseline_date))
                continue
            if (
                existing.baseline_date != baseline_date
                or existing.publication_event != publication.event
                or existing.publication_recorded_at != publication.recorded_at
            ):
                raise ValueError("existing bootstrap conflicts with immutable publication provenance")

        if not pending:
            return LifecycleBootstrapResult(
                status="ALREADY_BOOTSTRAPPED" if candidates else "NO_ELIGIBLE_ACTIVE_OPPORTUNITIES",
                batch_id=None,
                calendar_version=calendar_version,
                opportunity_count=0,
                batch_digest=None,
            )

        canonical_items = [
            {
                "signal_id": str(latest.signal_id),
                "baseline_date": baseline_date.isoformat(),
                "publication_event": publication.event,
                "publication_recorded_at": publication.recorded_at.isoformat(),
            }
            for latest, publication, baseline_date in sorted(pending, key=lambda item: str(item[0].signal_id))
        ]
        canonical_batch = {
            "calendar_version": calendar_version,
            "operator_id": operator_id,
            "reason": reason.strip(),
            "next_evaluation_date": next_evaluation_date.isoformat(),
            "opportunities": canonical_items,
        }
        digest = hashlib.sha256(
            json.dumps(canonical_batch, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        batch_id = uuid5(NAMESPACE_URL, f"egx-lifecycle-bootstrap:{digest}")
        batch = LifecycleBootstrapBatchRecord(
            batch_id=batch_id,
            calendar_version=calendar_version,
            operator_id=operator_id,
            reason=reason.strip(),
            recorded_at=recorded_at,
            opportunity_count=len(pending),
            batch_digest=digest,
        )
        bootstrap_records = tuple(
            LifecycleBootstrapRecord(
                batch_id=batch_id,
                signal_id=latest.signal_id,
                baseline_date=baseline_date,
                publication_event=publication.event,
                publication_recorded_at=publication.recorded_at,
                operator_id=operator_id,
                reason=reason.strip(),
                calendar_version=calendar_version,
                recorded_at=recorded_at,
                idempotency_key=f"{latest.signal_id}:{calendar_version}",
            )
            for latest, publication, baseline_date in sorted(
                pending, key=lambda item: str(item[0].signal_id)
            )
        )
        self._unit_of_work.execute(
            lambda transaction: transaction.record_bootstrap_batch(batch, bootstrap_records)
        )
        return LifecycleBootstrapResult(
            status="BOOTSTRAPPED",
            batch_id=str(batch_id),
            calendar_version=calendar_version,
            opportunity_count=len(bootstrap_records),
            batch_digest=digest,
        )
