from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.application.market_data.session_calendar_store import (
    CalendarActivationEvent,
    StoredCalendarVersion,
)
from app.domain.market_data.session_calendar import EGXSessionCalendar
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class CalendarVersionIntegrityError(RuntimeError):
    """Raised when a persisted calendar payload no longer matches its content hash."""


class SQLiteSessionCalendarRepository:
    """Persists immutable calendar versions and an audited active-version pointer."""

    def __init__(self, database_path: str | Path) -> None:
        self._memory_anchor: sqlite3.Connection | None = None
        self._closed = False
        if str(database_path) == ":memory:":
            self._database_path = (
                f"file:egx_session_calendar_{uuid4().hex}?mode=memory&cache=shared"
            )
            self._use_uri = True
            self._memory_anchor = connect_sqlite(self._database_path, uri=True)
        else:
            path = Path(database_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._database_path = str(path)
            self._use_uri = False
        try:
            self._initialize()
        except Exception:
            self.close()
            raise

    def _connect(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("Session calendar repository is closed")
        connection = connect_sqlite(self._database_path, uri=self._use_uri)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def close(self) -> None:
        if self._closed:
            return
        if self._memory_anchor is not None:
            self._memory_anchor.close()
            self._memory_anchor = None
        self._closed = True

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS egx_calendar_versions (
                    version TEXT PRIMARY KEY,
                    calendar_json TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    published_by TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    publication_reason TEXT NOT NULL
                );

                CREATE TRIGGER IF NOT EXISTS egx_calendar_versions_no_update
                BEFORE UPDATE ON egx_calendar_versions
                BEGIN
                    SELECT RAISE(ABORT, 'calendar versions are immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS egx_calendar_versions_no_delete
                BEFORE DELETE ON egx_calendar_versions
                BEGIN
                    SELECT RAISE(ABORT, 'calendar versions are immutable');
                END;

                CREATE TABLE IF NOT EXISTS egx_calendar_active_version (
                    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                    version TEXT NULL REFERENCES egx_calendar_versions(version)
                );

                INSERT OR IGNORE INTO egx_calendar_active_version(singleton_id, version)
                VALUES (1, NULL);

                CREATE TABLE IF NOT EXISTS egx_calendar_activation_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL CHECK (action IN ('ACTIVATE', 'DEACTIVATE', 'ROLLBACK')),
                    previous_version TEXT NULL,
                    target_version TEXT NULL,
                    occurred_at TEXT NOT NULL,
                    performed_by TEXT NOT NULL,
                    reason TEXT NOT NULL
                );

                CREATE TRIGGER IF NOT EXISTS egx_calendar_activation_events_no_update
                BEFORE UPDATE ON egx_calendar_activation_events
                BEGIN
                    SELECT RAISE(ABORT, 'calendar activation events are append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS egx_calendar_activation_events_no_delete
                BEFORE DELETE ON egx_calendar_activation_events
                BEGIN
                    SELECT RAISE(ABORT, 'calendar activation events are append-only');
                END;
                """
            )

    def publish(
        self,
        calendar: EGXSessionCalendar,
        *,
        published_by: str,
        source_reference: str,
        reason: str,
        published_at: datetime | None = None,
    ) -> StoredCalendarVersion:
        actor = self._required_text(published_by, "published_by")
        source = self._required_text(source_reference, "source_reference")
        publication_reason = self._required_text(reason, "reason")
        timestamp = self._aware_utc(published_at or datetime.now(timezone.utc))
        payload = self._calendar_payload(calendar)
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        with self._connect() as connection:
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
        return StoredCalendarVersion(
            calendar.version, calendar, digest, timestamp, actor, source, publication_reason
        )

    def get_version(self, version: str) -> StoredCalendarVersion | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT version, calendar_json, sha256, published_at,
                       published_by, source_reference, publication_reason
                FROM egx_calendar_versions WHERE version = ?
                """,
                (version,),
            ).fetchone()
        return self._version_from_row(row) if row else None

    def list_versions(self) -> tuple[StoredCalendarVersion, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT version, calendar_json, sha256, published_at,
                       published_by, source_reference, publication_reason
                FROM egx_calendar_versions
                ORDER BY published_at ASC, version ASC
                """
            ).fetchall()
        return tuple(self._version_from_row(row) for row in rows)

    def get_active(self) -> StoredCalendarVersion | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT v.version, v.calendar_json, v.sha256, v.published_at,
                       v.published_by, v.source_reference, v.publication_reason
                FROM egx_calendar_active_version AS a
                JOIN egx_calendar_versions AS v ON v.version = a.version
                WHERE a.singleton_id = 1
                """
            ).fetchone()
        return self._version_from_row(row) if row else None

    def activate(
        self,
        version: str,
        *,
        performed_by: str,
        reason: str,
        occurred_at: datetime | None = None,
    ) -> CalendarActivationEvent:
        return self._change_active(
            action="ACTIVATE",
            target_version=version,
            performed_by=performed_by,
            reason=reason,
            occurred_at=occurred_at,
        )

    def rollback(
        self,
        version: str,
        *,
        performed_by: str,
        reason: str,
        occurred_at: datetime | None = None,
    ) -> CalendarActivationEvent:
        return self._change_active(
            action="ROLLBACK",
            target_version=version,
            performed_by=performed_by,
            reason=reason,
            occurred_at=occurred_at,
            require_previously_active=True,
        )

    def deactivate(
        self,
        *,
        performed_by: str,
        reason: str,
        occurred_at: datetime | None = None,
    ) -> CalendarActivationEvent:
        return self._change_active(
            action="DEACTIVATE",
            target_version=None,
            performed_by=performed_by,
            reason=reason,
            occurred_at=occurred_at,
        )

    def list_activation_events(self) -> tuple[CalendarActivationEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, action, previous_version, target_version,
                       occurred_at, performed_by, reason
                FROM egx_calendar_activation_events
                ORDER BY event_id ASC
                """
            ).fetchall()
        return tuple(self._event_from_row(row) for row in rows)

    def _change_active(
        self,
        *,
        action: str,
        target_version: str | None,
        performed_by: str,
        reason: str,
        occurred_at: datetime | None,
        require_previously_active: bool = False,
    ) -> CalendarActivationEvent:
        actor = self._required_text(performed_by, "performed_by")
        audit_reason = self._required_text(reason, "reason")
        timestamp = self._aware_utc(occurred_at or datetime.now(timezone.utc))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if target_version is not None:
                target_row = connection.execute(
                    """
                    SELECT version, calendar_json, sha256, published_at,
                           published_by, source_reference, publication_reason
                    FROM egx_calendar_versions WHERE version = ?
                    """,
                    (target_version,),
                ).fetchone()
                if target_row is None:
                    raise KeyError(f"Unknown calendar version: {target_version}")
                # Never activate or roll back to a version whose persisted payload
                # no longer passes the same integrity checks used by read operations.
                self._version_from_row(target_row)
            current_row = connection.execute(
                "SELECT version FROM egx_calendar_active_version WHERE singleton_id = 1"
            ).fetchone()
            previous = current_row[0] if current_row else None
            if action == "DEACTIVATE" and previous is None:
                raise ValueError("Cannot deactivate when no calendar version is active")
            if action in {"ACTIVATE", "ROLLBACK"} and previous == target_version:
                raise ValueError("Target calendar version is already active")
            if require_previously_active:
                was_active = connection.execute(
                    """
                    SELECT 1 FROM egx_calendar_activation_events
                    WHERE target_version = ? AND action IN ('ACTIVATE', 'ROLLBACK')
                    LIMIT 1
                    """,
                    (target_version,),
                ).fetchone()
                if was_active is None:
                    raise ValueError("Rollback target must have been active previously")
            connection.execute(
                "UPDATE egx_calendar_active_version SET version = ? WHERE singleton_id = 1",
                (target_version,),
            )
            cursor = connection.execute(
                """
                INSERT INTO egx_calendar_activation_events (
                    action, previous_version, target_version,
                    occurred_at, performed_by, reason
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    action, previous, target_version, timestamp.isoformat(), actor, audit_reason
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not return an activation event id")
            event_id = cursor.lastrowid
        return CalendarActivationEvent(
            event_id, action, previous, target_version, timestamp, actor, audit_reason
        )

    @staticmethod
    def _calendar_payload(calendar: EGXSessionCalendar) -> dict:
        return {
            "version": calendar.version,
            "timezone": calendar.timezone,
            "coverage_start": calendar.coverage_start.isoformat(),
            "coverage_end": calendar.coverage_end.isoformat(),
            "days": [
                {
                    "date": day.session_date.isoformat(),
                    "status": day.status.value,
                    "session_open": day.session_open.isoformat() if day.session_open else None,
                    "session_close": day.session_close.isoformat() if day.session_close else None,
                    "closed_at": day.closed_at.isoformat() if day.closed_at else None,
                    "reason": day.reason,
                }
                for day in calendar.days
            ],
        }

    @staticmethod
    def _version_from_row(row: tuple) -> StoredCalendarVersion:
        version, payload, digest, published_at, published_by, source, reason = row
        try:
            decoded_payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError) as error:
            raise CalendarVersionIntegrityError(
                f"Stored calendar version {version!r} contains invalid JSON"
            ) from error
        canonical_payload = json.dumps(
            decoded_payload, sort_keys=True, separators=(",", ":")
        )
        actual_digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual_digest, digest):
            raise CalendarVersionIntegrityError(
                f"Stored calendar version {version!r} failed its SHA-256 integrity check"
            )
        try:
            calendar = EGXSessionCalendar.from_dict(decoded_payload)
        except (TypeError, ValueError) as error:
            raise CalendarVersionIntegrityError(
                f"Stored calendar version {version!r} contains an invalid calendar"
            ) from error
        if calendar.version != version:
            raise CalendarVersionIntegrityError(
                f"Stored calendar row {version!r} does not match its payload version"
            )
        return StoredCalendarVersion(
            version, calendar, digest, datetime.fromisoformat(published_at),
            published_by, source, reason
        )

    @staticmethod
    def _event_from_row(row: tuple) -> CalendarActivationEvent:
        event_id, action, previous, target, occurred_at, actor, reason = row
        return CalendarActivationEvent(
            event_id, action, previous, target, datetime.fromisoformat(occurred_at), actor, reason
        )

    @staticmethod
    def _required_text(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be non-empty")
        return value.strip()

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Audit timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
