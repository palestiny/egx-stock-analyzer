from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.api.session_opportunity_ledger_response import SessionOpportunityLedgerResponse
from app.domain.reporting.session_opportunity_ledger import SessionOpportunityLedgerReport
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteSessionOpportunityReportStore:
    """Immutable, versioned snapshots of end-of-session opportunity reports."""

    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_opportunity_reports (
                    session_date TEXT NOT NULL,
                    methodology_version TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    total_count INTEGER NOT NULL,
                    unresolved_count INTEGER NOT NULL,
                    resolved_proxy_count INTEGER NOT NULL,
                    PRIMARY KEY(session_date, methodology_version, generated_at)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_opportunity_reports_latest
                ON session_opportunity_reports(session_date, generated_at DESC)
                """
            )

    def save(self, report: SessionOpportunityLedgerReport) -> bool:
        if report.generated_at.tzinfo is None or report.generated_at.utcoffset() is None:
            raise ValueError("report.generated_at must be timezone-aware")
        payload = json.dumps(
            SessionOpportunityLedgerResponse.from_report(report),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        values = (
            report.session_date.isoformat(),
            report.methodology_version,
            report.generated_at.astimezone(timezone.utc).isoformat(),
        )
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT report_json FROM session_opportunity_reports
                WHERE session_date = ? AND methodology_version = ? AND generated_at = ?
                """,
                values,
            ).fetchone()
            if existing is not None:
                if str(existing[0]) != payload:
                    raise ValueError("session report snapshot is immutable")
                return False
            connection.execute(
                """
                INSERT INTO session_opportunity_reports(
                    session_date, methodology_version, generated_at, report_json,
                    total_count, unresolved_count, resolved_proxy_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (*values, payload, report.total_count, report.unresolved_count, report.resolved_proxy_count),
            )
        return True

    def get_latest(
        self,
        session_date: date,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, Any] | None:
        cutoff = as_of or datetime.now(timezone.utc)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT report_json FROM session_opportunity_reports
                WHERE session_date = ? AND generated_at <= ?
                ORDER BY generated_at DESC, methodology_version ASC
                LIMIT 1
                """,
                (session_date.isoformat(), cutoff.astimezone(timezone.utc).isoformat()),
            ).fetchone()
        if row is None:
            return None
        value = json.loads(str(row[0]))
        if not isinstance(value, dict):
            raise ValueError("stored session report is invalid")
        return value
