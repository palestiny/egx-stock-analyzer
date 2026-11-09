from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

from app.domain.market_data.calendar_evidence import (
    CalendarEvidence,
    CalendarEvidenceKind,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class CalendarEvidenceIntegrityError(RuntimeError):
    """Raised when stored evidence no longer matches its canonical digest."""


@dataclass(frozen=True)
class CalendarEvidenceConflict:
    calendar_version: str
    session_date: date
    evidence_kind: CalendarEvidenceKind
    evidence: tuple[CalendarEvidence, ...]


class SQLiteCalendarEvidenceRepository:
    """Append-only, hash-verified evidence records for explicit EGX calendar days."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = connect_sqlite(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS egx_calendar_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    calendar_version TEXT NOT NULL
                        REFERENCES egx_calendar_versions(version),
                    session_date TEXT NOT NULL,
                    evidence_kind TEXT NOT NULL CHECK (
                        evidence_kind IN (
                            'SCHEDULE', 'CLOSURE', 'CANCELLATION',
                            'EXCEPTIONAL_HOURS', 'CLOSE_CONFIRMATION'
                        )
                    ),
                    source_type TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    recorded_by TEXT NOT NULL REFERENCES users(id),
                    observed_at TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    source_published_at TEXT NULL,
                    supersedes_evidence_id TEXT NULL
                        REFERENCES egx_calendar_evidence(evidence_id),
                    supersession_reason TEXT NULL,
                    content_sha256 TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_calendar_evidence_day
                ON egx_calendar_evidence(calendar_version, session_date, evidence_kind);

                CREATE TRIGGER IF NOT EXISTS egx_calendar_evidence_no_update
                BEFORE UPDATE ON egx_calendar_evidence
                BEGIN
                    SELECT RAISE(ABORT, 'calendar evidence is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS egx_calendar_evidence_no_delete
                BEFORE DELETE ON egx_calendar_evidence
                BEGIN
                    SELECT RAISE(ABORT, 'calendar evidence is immutable');
                END;
                """
            )

    def append(self, evidence: CalendarEvidence) -> CalendarEvidence:
        if evidence.content_sha256:
            raise ValueError("New evidence must not supply a precomputed content hash")
        if evidence.recorded_at > datetime.now(timezone.utc):
            raise ValueError("recorded_at cannot be in the future")
        if evidence.supersedes_evidence_id == evidence.evidence_id:
            raise ValueError("Evidence cannot supersede itself")
        payload = self._payload(evidence)
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            calendar_row = connection.execute(
                "SELECT calendar_json FROM egx_calendar_versions WHERE version = ?",
                (evidence.calendar_version,),
            ).fetchone()
            if calendar_row is None:
                raise KeyError(f"Unknown calendar version: {evidence.calendar_version}")
            calendar_payload = json.loads(calendar_row[0])
            covered_dates = {
                item.get("date") for item in calendar_payload.get("days", [])
            }
            if evidence.session_date.isoformat() not in covered_dates:
                raise ValueError(
                    "Evidence session_date must be an explicit date in the calendar version"
                )
            if evidence.supersedes_evidence_id is not None:
                prior = connection.execute(
                    """
                    SELECT calendar_version, session_date, evidence_kind
                    FROM egx_calendar_evidence WHERE evidence_id = ?
                    """,
                    (str(evidence.supersedes_evidence_id),),
                ).fetchone()
                if prior is None:
                    raise KeyError("Superseded evidence does not exist")
                expected = (
                    evidence.calendar_version,
                    evidence.session_date.isoformat(),
                    evidence.evidence_kind.value,
                )
                if prior != expected:
                    raise ValueError("Superseding evidence must support the same calendar day and kind")
            connection.execute(
                """
                INSERT INTO egx_calendar_evidence (
                    evidence_id, calendar_version, session_date, evidence_kind,
                    source_type, source_reference, claim, recorded_by, observed_at,
                    recorded_at, source_published_at, supersedes_evidence_id,
                    supersession_reason, content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(evidence.evidence_id),
                    evidence.calendar_version,
                    evidence.session_date.isoformat(),
                    evidence.evidence_kind.value,
                    evidence.source_type,
                    evidence.source_reference,
                    evidence.claim,
                    str(evidence.recorded_by),
                    evidence.observed_at.astimezone(timezone.utc).isoformat(),
                    evidence.recorded_at.astimezone(timezone.utc).isoformat(),
                    evidence.source_published_at.astimezone(timezone.utc).isoformat()
                    if evidence.source_published_at else None,
                    str(evidence.supersedes_evidence_id)
                    if evidence.supersedes_evidence_id else None,
                    evidence.supersession_reason,
                    digest,
                ),
            )
        stored = self.get(evidence.evidence_id)
        if stored is None:
            raise RuntimeError("Persisted calendar evidence could not be read back")
        return stored

    def get(self, evidence_id: UUID) -> CalendarEvidence | None:
        with self._connect() as connection:
            row = connection.execute(
                self._select() + " WHERE evidence_id = ?",
                (str(evidence_id),),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_for_day(
        self, calendar_version: str, session_date: date
    ) -> tuple[CalendarEvidence, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                self._select()
                + " WHERE calendar_version = ? AND session_date = ?"
                + " ORDER BY recorded_at ASC, evidence_id ASC",
                (calendar_version, session_date.isoformat()),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def list_conflicts(
        self, calendar_version: str, session_date: date
    ) -> tuple[CalendarEvidenceConflict, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                self._select()
                + " WHERE calendar_version = ? AND session_date = ?"
                + " AND evidence_id NOT IN ("
                + " SELECT supersedes_evidence_id FROM egx_calendar_evidence"
                + " WHERE supersedes_evidence_id IS NOT NULL)"
                + " ORDER BY recorded_at ASC, evidence_id ASC",
                (calendar_version, session_date.isoformat()),
            ).fetchall()
        records = tuple(self._from_row(row) for row in rows)
        grouped: dict[CalendarEvidenceKind, list[CalendarEvidence]] = {}
        for record in records:
            grouped.setdefault(record.evidence_kind, []).append(record)
        return tuple(
            CalendarEvidenceConflict(
                calendar_version=calendar_version,
                session_date=session_date,
                evidence_kind=kind,
                evidence=tuple(items),
            )
            for kind, items in grouped.items()
            if len({item.claim for item in items}) > 1
        )

    @staticmethod
    def _select() -> str:
        return """
            SELECT evidence_id, calendar_version, session_date, evidence_kind,
                   source_type, source_reference, claim, recorded_by, observed_at,
                   recorded_at, source_published_at, supersedes_evidence_id,
                   supersession_reason, content_sha256
            FROM egx_calendar_evidence
        """

    @staticmethod
    def _payload(evidence: CalendarEvidence) -> dict:
        return {
            "evidence_id": str(evidence.evidence_id),
            "calendar_version": evidence.calendar_version,
            "session_date": evidence.session_date.isoformat(),
            "evidence_kind": evidence.evidence_kind.value,
            "source_type": evidence.source_type,
            "source_reference": evidence.source_reference,
            "claim": evidence.claim,
            "recorded_by": str(evidence.recorded_by),
            "observed_at": evidence.observed_at.astimezone(timezone.utc).isoformat(),
            "recorded_at": evidence.recorded_at.astimezone(timezone.utc).isoformat(),
            "source_published_at": evidence.source_published_at.astimezone(timezone.utc).isoformat()
            if evidence.source_published_at else None,
            "supersedes_evidence_id": str(evidence.supersedes_evidence_id)
            if evidence.supersedes_evidence_id else None,
            "supersession_reason": evidence.supersession_reason,
        }

    @classmethod
    def _from_row(cls, row: tuple) -> CalendarEvidence:
        (
            raw_id, version, raw_date, raw_kind, source_type, source_reference,
            claim, actor, observed, recorded, source_published, supersedes,
            supersession_reason, digest,
        ) = row
        evidence = CalendarEvidence(
            evidence_id=UUID(raw_id),
            calendar_version=version,
            session_date=date.fromisoformat(raw_date),
            evidence_kind=CalendarEvidenceKind(raw_kind),
            source_type=source_type,
            source_reference=source_reference,
            claim=claim,
            recorded_by=UUID(actor),
            observed_at=datetime.fromisoformat(observed),
            recorded_at=datetime.fromisoformat(recorded),
            source_published_at=datetime.fromisoformat(source_published)
            if source_published else None,
            supersedes_evidence_id=UUID(supersedes) if supersedes else None,
            supersession_reason=supersession_reason,
            content_sha256=digest,
        )
        canonical = json.dumps(cls._payload(evidence), sort_keys=True, separators=(",", ":"))
        actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual, digest):
            raise CalendarEvidenceIntegrityError(
                f"Calendar evidence {raw_id!r} failed its SHA-256 integrity check"
            )
        return evidence
