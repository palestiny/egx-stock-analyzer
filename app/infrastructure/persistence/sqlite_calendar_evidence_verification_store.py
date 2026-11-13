from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.market_data.calendar_source_authenticity import (
    CalendarEvidenceVerificationRecord,
    CalendarEvidenceVerificationStore,
    CalendarSourceVerificationDecision,
)
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteCalendarEvidenceVerificationStore(CalendarEvidenceVerificationStore):
    """Append-only persistence for independent calendar-source verification outcomes."""

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
                CREATE TABLE IF NOT EXISTS egx_calendar_evidence_verifications (
                    verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evidence_id TEXT NOT NULL REFERENCES egx_calendar_evidence(evidence_id),
                    decision TEXT NOT NULL CHECK (decision IN ('VERIFIED', 'REJECTED')),
                    source_origin TEXT NOT NULL,
                    registry_version TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL CHECK (length(artifact_sha256) = 64),
                    verifier_user_id TEXT NOT NULL REFERENCES users(id),
                    verifier_credential_id TEXT NOT NULL,
                    uploader_user_id TEXT NOT NULL REFERENCES users(id),
                    uploader_credential_id TEXT NOT NULL,
                    reviewed_claim_sha256 TEXT NOT NULL CHECK (length(reviewed_claim_sha256) = 64),
                    method_version TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    CHECK (
                        verifier_user_id <> uploader_user_id
                        AND verifier_credential_id <> uploader_credential_id
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_calendar_evidence_verification_latest
                ON egx_calendar_evidence_verifications(evidence_id, verification_id);

                CREATE TRIGGER IF NOT EXISTS egx_calendar_evidence_verifications_no_update
                BEFORE UPDATE ON egx_calendar_evidence_verifications
                BEGIN
                    SELECT RAISE(ABORT, 'calendar evidence verification records are immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS egx_calendar_evidence_verifications_no_delete
                BEFORE DELETE ON egx_calendar_evidence_verifications
                BEGIN
                    SELECT RAISE(ABORT, 'calendar evidence verification records are immutable');
                END;
                """
            )

    def append(self, record: CalendarEvidenceVerificationRecord) -> None:
        if record.verifier_user_id == record.uploader_user_id:
            raise ValueError("Independent reviewer must differ from uploader")
        if record.verifier_credential_id == record.uploader_credential_id:
            raise ValueError("Independent reviewer credential must differ from uploader credential")
        with self._connect() as connection:
            self._require_active_operator_credential(
                connection, record.verifier_user_id, record.verifier_credential_id
            )
            self._require_active_operator_credential(
                connection, record.uploader_user_id, record.uploader_credential_id
            )
            connection.execute(
                """
                INSERT INTO egx_calendar_evidence_verifications (
                    evidence_id, decision, source_origin, registry_version,
                    artifact_sha256, verifier_user_id, verifier_credential_id,
                    uploader_user_id, uploader_credential_id, reviewed_claim_sha256,
                    method_version, verified_at, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(record.evidence_id),
                    record.decision.value,
                    record.source_origin,
                    record.registry_version,
                    record.artifact_sha256,
                    str(record.verifier_user_id),
                    str(record.verifier_credential_id),
                    str(record.uploader_user_id),
                    str(record.uploader_credential_id),
                    record.reviewed_claim_sha256,
                    record.method_version,
                    record.verified_at.isoformat(),
                    record.reason,
                ),
            )

    @staticmethod
    def _require_active_operator_credential(
        connection: sqlite3.Connection,
        user_id: UUID,
        credential_id: UUID,
    ) -> None:
        row = connection.execute(
            """
            SELECT 1
            FROM operator_access_current AS grants
            JOIN users AS users ON users.id = grants.user_id
            JOIN user_credentials AS credentials ON credentials.user_id = users.id
            WHERE users.id = ?
              AND users.status = 'active'
              AND credentials.id = ?
              AND credentials.status = 'active'
            """,
            (str(user_id), str(credential_id)),
        ).fetchone()
        if row is None:
            raise ValueError(
                "Uploader and reviewer must both have active individual operator credentials"
            )

    def latest(self, evidence_id: UUID) -> CalendarEvidenceVerificationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT evidence_id, decision, source_origin, registry_version,
                       artifact_sha256, verifier_user_id, verifier_credential_id,
                       uploader_user_id, uploader_credential_id, reviewed_claim_sha256,
                       method_version, verified_at, reason
                FROM egx_calendar_evidence_verifications
                WHERE evidence_id = ?
                ORDER BY verification_id DESC
                LIMIT 1
                """,
                (str(evidence_id),),
            ).fetchone()
        if row is None:
            return None
        return CalendarEvidenceVerificationRecord(
            evidence_id=UUID(row[0]),
            decision=CalendarSourceVerificationDecision(row[1]),
            source_origin=row[2],
            registry_version=row[3],
            artifact_sha256=row[4],
            verifier_user_id=UUID(row[5]),
            verifier_credential_id=UUID(row[6]),
            uploader_user_id=UUID(row[7]),
            uploader_credential_id=UUID(row[8]),
            reviewed_claim_sha256=row[9],
            method_version=row[10],
            verified_at=datetime.fromisoformat(row[11]),
            reason=row[12],
        )
