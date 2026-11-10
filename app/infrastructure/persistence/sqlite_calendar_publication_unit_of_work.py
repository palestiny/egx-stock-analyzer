from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from uuid import UUID

from app.application.market_data.session_calendar_store import StoredCalendarVersion
from app.application.market_data.calendar_artifact_storage import (
    CalendarArtifactService,
    CalendarArtifactStorageNotConfiguredError,
)
from app.domain.market_data.calendar_evidence import CalendarArtifactRetention, CalendarEvidence, CalendarEvidenceKind, CalendarEvidenceSourceClass
from app.domain.market_data.session_calendar import CalendarDayStatus, EGXSessionCalendar
from app.infrastructure.persistence.sqlite_calendar_evidence_repository import (
    SQLiteCalendarEvidenceRepository,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)


class SQLiteCalendarPublicationUnitOfWork:
    """Atomically publishes one immutable calendar version and its day evidence."""

    def __init__(
        self,
        calendar_repository: SQLiteSessionCalendarRepository,
        evidence_repository: SQLiteCalendarEvidenceRepository,
        artifact_service: CalendarArtifactService | None = None,
    ) -> None:
        calendar_path = Path(calendar_repository._database_path).resolve()
        evidence_path = Path(evidence_repository._database_path).resolve()
        if calendar_path != evidence_path:
            raise ValueError("calendar and evidence repositories must share one SQLite database")
        self._database_path = str(calendar_path)
        self._calendar_repository = calendar_repository
        self._evidence_repository = evidence_repository
        self._artifact_service = artifact_service
        self._initialize_links()

    def _initialize_links(self) -> None:
        with connect_sqlite(self._database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS egx_calendar_day_evidence_links (
                    calendar_version TEXT NOT NULL
                        REFERENCES egx_calendar_versions(version),
                    session_date TEXT NOT NULL,
                    evidence_id TEXT NOT NULL
                        REFERENCES egx_calendar_evidence(evidence_id),
                    PRIMARY KEY (calendar_version, session_date, evidence_id)
                );

                CREATE TRIGGER IF NOT EXISTS egx_calendar_day_evidence_link_validate
                BEFORE INSERT ON egx_calendar_day_evidence_links
                WHEN NOT EXISTS (
                    SELECT 1 FROM egx_calendar_evidence e
                    WHERE e.evidence_id = NEW.evidence_id
                      AND e.calendar_version = NEW.calendar_version
                      AND e.session_date = NEW.session_date
                )
                BEGIN
                    SELECT RAISE(ABORT, 'calendar evidence link must match evidence version and date');
                END;

                CREATE TRIGGER IF NOT EXISTS egx_calendar_day_evidence_links_no_update
                BEFORE UPDATE ON egx_calendar_day_evidence_links
                BEGIN
                    SELECT RAISE(ABORT, 'calendar evidence links are immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS egx_calendar_day_evidence_links_no_delete
                BEFORE DELETE ON egx_calendar_day_evidence_links
                BEGIN
                    SELECT RAISE(ABORT, 'calendar evidence links are immutable');
                END;
                """
            )

    def publish(
        self,
        calendar: EGXSessionCalendar,
        evidence: Sequence[CalendarEvidence],
        *,
        published_by: str,
        source_reference: str,
        reason: str,
        published_at: datetime | None = None,
    ) -> tuple[StoredCalendarVersion, tuple[CalendarEvidence, ...]]:
        actor = self._calendar_repository._required_text(published_by, "published_by")
        source = self._calendar_repository._required_text(source_reference, "source_reference")
        publication_reason = self._calendar_repository._required_text(reason, "reason")
        timestamp = self._calendar_repository._aware_utc(
            published_at or datetime.now(timezone.utc)
        )
        actor_id = UUID(actor)
        calendar_dates = {day.session_date for day in calendar.days}
        evidence_dates = {item.session_date for item in evidence}
        if not evidence:
            raise ValueError("Evidence is required for every explicit calendar date")
        if evidence_dates != calendar_dates:
            missing_dates = sorted(day.isoformat() for day in calendar_dates - evidence_dates)
            extra_dates = sorted(day.isoformat() for day in evidence_dates - calendar_dates)
            raise ValueError(
                f"Evidence must cover exactly the calendar dates; missing={missing_dates}, extra={extra_dates}"
            )
        if any(item.calendar_version != calendar.version for item in evidence):
            raise ValueError("Every evidence record must reference the calendar version being published")
        if any(item.recorded_by != actor_id for item in evidence):
            raise ValueError("Evidence actor must match the authenticated calendar publisher")
        if any(item.source_class is None for item in evidence):
            raise ValueError("Every newly published evidence record requires explicit source acceptance metadata")
        if len({item.evidence_id for item in evidence}) != len(evidence):
            raise ValueError("Evidence identifiers must be unique within a publication")
        archived_evidence = [
            item
            for item in evidence
            if item.artifact_retention is CalendarArtifactRetention.ARCHIVED
        ]
        if archived_evidence:
            if self._artifact_service is None:
                raise CalendarArtifactStorageNotConfiguredError(
                    "Verified calendar artifact storage is required for ARCHIVED evidence"
                )
            for item in archived_evidence:
                self._artifact_service.verify(
                    item.artifact_storage_reference or "",
                    item.artifact_sha256 or "",
                )
        evidence_kinds_by_date: dict = {}
        for item in evidence:
            evidence_kinds_by_date.setdefault(item.session_date, set()).add(item.evidence_kind)
        for day in calendar.days:
            required_kinds = {
                CalendarDayStatus.NON_TRADING: {CalendarEvidenceKind.CLOSURE},
                CalendarDayStatus.CANCELLED: {CalendarEvidenceKind.CANCELLATION},
                CalendarDayStatus.SCHEDULED: {CalendarEvidenceKind.SCHEDULE},
                CalendarDayStatus.OPEN: {CalendarEvidenceKind.SCHEDULE, CalendarEvidenceKind.OPEN_CONFIRMATION},
                CalendarDayStatus.CLOSED: {
                    CalendarEvidenceKind.SCHEDULE,
                    CalendarEvidenceKind.CLOSE_CONFIRMATION,
                },
            }[day.status]
            day_evidence_kinds = evidence_kinds_by_date.get(day.session_date, set())
            if (
                CalendarEvidenceKind.EXCEPTIONAL_HOURS in day_evidence_kinds
                and not day.exceptional_hours
            ):
                raise ValueError(
                    f"Calendar date {day.session_date.isoformat()} has exceptional-hours evidence without an explicit day marker"
                )
            if day.exceptional_hours:
                required_kinds = required_kinds | {CalendarEvidenceKind.EXCEPTIONAL_HOURS}
            missing_kinds = required_kinds - day_evidence_kinds
            accepted_primary_kinds = {
                item.evidence_kind for item in evidence
                if item.session_date == day.session_date
                and item.source_class is CalendarEvidenceSourceClass.A
                and item.market_scope == "EGX_MARKET_WIDE"
                and item.effective_from is not None
                and item.effective_through is not None
                and item.effective_from <= day.session_date <= item.effective_through
            }
            missing_primary_kinds = required_kinds - accepted_primary_kinds
            if any(
                item.session_date == day.session_date
                and item.evidence_kind is CalendarEvidenceKind.EXCEPTIONAL_HOURS
                and not (
                    item.source_class is CalendarEvidenceSourceClass.A
                    and item.market_scope == "EGX_MARKET_WIDE"
                    and item.effective_from is not None
                    and item.effective_through is not None
                    and item.effective_from <= day.session_date <= item.effective_through
                )
                for item in evidence
            ):
                raise ValueError(
                    f"Exceptional-hours evidence for {day.session_date.isoformat()} requires Class A EGX primary evidence"
                )
            if missing_kinds:
                missing_kind_names = ", ".join(sorted(kind.value for kind in missing_kinds))
                raise ValueError(
                    f"Calendar date {day.session_date.isoformat()} requires evidence kinds: {missing_kind_names}"
                )
            if missing_primary_kinds:
                names = ", ".join(sorted(kind.value for kind in missing_primary_kinds))
                raise ValueError(
                    f"Calendar date {day.session_date.isoformat()} requires Class A EGX primary evidence kinds: {names}"
                )

        payload = self._calendar_repository._calendar_payload(calendar)
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        stored_evidence: list[CalendarEvidence] = []

        connection = connect_sqlite(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO egx_calendar_versions (
                    version, calendar_json, sha256, published_at,
                    published_by, source_reference, publication_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    calendar.version,
                    serialized,
                    digest,
                    timestamp.isoformat(),
                    actor,
                    source,
                    publication_reason,
                ),
            )
            for item in evidence:
                stored = self._evidence_repository.append_in_transaction(connection, item)
                connection.execute(
                    """
                    INSERT INTO egx_calendar_day_evidence_links (
                        calendar_version, session_date, evidence_id
                    ) VALUES (?, ?, ?)
                    """,
                    (calendar.version, item.session_date.isoformat(), str(item.evidence_id)),
                )
                stored_evidence.append(stored)

            self._validate_no_unresolved_conflicts(connection, calendar.version, calendar_dates)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return (
            StoredCalendarVersion(
                calendar.version,
                calendar,
                digest,
                timestamp,
                actor,
                source,
                publication_reason,
            ),
            tuple(stored_evidence),
        )

    @staticmethod
    def _validate_no_unresolved_conflicts(
        connection: sqlite3.Connection,
        calendar_version: str,
        session_dates: set,
    ) -> None:
        for session_date in session_dates:
            rows = connection.execute(
                """
                SELECT evidence_kind, claim
                FROM egx_calendar_evidence
                WHERE calendar_version = ?
                  AND session_date = ?
                  AND evidence_id NOT IN (
                      SELECT supersedes_evidence_id
                      FROM egx_calendar_evidence
                      WHERE supersedes_evidence_id IS NOT NULL
                  )
                """,
                (calendar_version, session_date.isoformat()),
            ).fetchall()
            claims: dict[str, set[str]] = {}
            for kind, claim in rows:
                claims.setdefault(str(kind), set()).add(str(claim))
            if any(len(values) > 1 for values in claims.values()):
                raise ValueError(
                    f"Unresolved calendar evidence conflict for {session_date.isoformat()}"
                )

