from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

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
            self._report_payload(report),
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
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO session_opportunity_reports(
                    session_date, methodology_version, generated_at, report_json,
                    total_count, unresolved_count, resolved_proxy_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (*values, payload, report.total_count, report.unresolved_count, report.resolved_proxy_count),
            )
            if cursor.rowcount == 1:
                return True

            existing = connection.execute(
                """
                SELECT report_json FROM session_opportunity_reports
                WHERE session_date = ? AND methodology_version = ? AND generated_at = ?
                """,
                values,
            ).fetchone()
            if existing is None:
                raise RuntimeError("session report snapshot conflict was not persisted")
            if str(existing[0]) != payload:
                raise ValueError("session report snapshot is immutable")
        return False

    @staticmethod
    def _report_payload(report: SessionOpportunityLedgerReport) -> dict[str, Any]:
        return {
            "session_date": report.session_date.isoformat(),
            "generated_at": report.generated_at.astimezone(timezone.utc).isoformat(),
            "exchange_timezone": report.exchange_timezone,
            "methodology_version": report.methodology_version,
            "total_count": report.total_count,
            "unresolved_count": report.unresolved_count,
            "resolved_proxy_count": report.resolved_proxy_count,
            "status_counts": dict(report.status_counts),
            "opportunities": [
                {
                    "signal_id": str(item.signal_id),
                    "symbol": item.symbol,
                    "publication_time": item.publication_time.isoformat(),
                    "original_entry_lower": str(item.original_entry_lower),
                    "original_entry_upper": str(item.original_entry_upper),
                    "original_invalidation": str(item.original_invalidation),
                    "original_targets": [
                        {"label": label, "price": str(price)}
                        for label, price in item.original_targets
                    ],
                    "current_status": item.current_status.value,
                    "current_evidence": list(item.current_evidence),
                    "market_proxy_outcome": item.market_proxy_outcome.value if item.market_proxy_outcome else None,
                    "market_proxy_return": str(item.market_proxy_return) if item.market_proxy_return is not None else None,
                    "market_proxy_r": str(item.market_proxy_r) if item.market_proxy_r is not None else None,
                    "outcome_observed_at": item.outcome_observed_at.isoformat() if item.outcome_observed_at else None,
                }
                for item in report.opportunities
            ],
        }

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
