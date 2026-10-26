from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteOwnerDashboardReadStore:
    """Read-only, aggregate-only operational snapshot over existing SQLite stores."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)

    def snapshot(self, *, as_of: datetime) -> dict[str, Any]:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        with connect_sqlite(self._database_path) as connection:
            tables = self._table_names(connection)
            outbox = self._status_counts(connection, tables, "signal_alert_outbox", "status")
            deliveries = self._status_counts(connection, tables, "signal_alert_deliveries", "status")
            subscriptions = self._status_counts(connection, tables, "subscriptions", "status")
            linked_accounts = self._count(connection, tables, "telegram_account_links")
            news_events = self._count(connection, tables, "news_events")
            session_reports = self._count(connection, tables, "session_opportunity_reports")
            pending_challenges = self._count_where(
                connection,
                tables,
                "telegram_link_challenges",
                "consumed_at IS NULL AND expires_at > ?",
                (as_of.isoformat(),),
            )
            outbox_oldest_pending = self._oldest_pending_outbox(connection, tables)

        return {
            "as_of": as_of.isoformat(),
            "availability": {
                "telegram_outbox": outbox is not None,
                "telegram_delivery_history": deliveries is not None,
                "subscriptions": subscriptions is not None,
                "telegram_account_links": linked_accounts is not None,
                "news_events": news_events is not None,
                "session_reports": "session_opportunity_reports" in tables,
                "payment_reconciliation": "payment_events" in tables,
            },
            "counts": {
                "telegram_outbox_by_status": outbox,
                "telegram_deliveries_by_status": deliveries,
                "subscriptions_by_status": subscriptions,
                "linked_telegram_accounts": linked_accounts,
                "unconsumed_unexpired_link_challenges": pending_challenges,
                "news_events": news_events,
                "saved_session_reports": session_reports,
                "oldest_pending_outbox_created_at": outbox_oldest_pending,
            },
            "limitations": [
                "Telegram transport acceptance does not prove a message was read.",
                "Session-report persistence and payment reconciliation are not configured unless their availability flags are true.",
                "This is an aggregate operational view; it does not expose chat IDs, tokens, payment references, or subscriber personal data.",
            ],
        }

    @staticmethod
    def _table_names(connection: sqlite3.Connection) -> set[str]:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {str(row[0]) for row in rows}

    @classmethod
    def _count(
        cls,
        connection: sqlite3.Connection,
        tables: set[str],
        table: str,
    ) -> int | None:
        if table not in tables:
            return None
        row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])

    @classmethod
    def _count_where(
        cls,
        connection: sqlite3.Connection,
        tables: set[str],
        table: str,
        where_clause: str,
        parameters: tuple[object, ...],
    ) -> int | None:
        if table not in tables:
            return None
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {where_clause}",
            parameters,
        ).fetchone()
        return int(row[0])

    @classmethod
    def _status_counts(
        cls,
        connection: sqlite3.Connection,
        tables: set[str],
        table: str,
        status_column: str,
    ) -> dict[str, int] | None:
        if table not in tables:
            return None
        rows = connection.execute(
            f"SELECT {status_column}, COUNT(*) FROM {table} GROUP BY {status_column}"
        ).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    @classmethod
    def _oldest_pending_outbox(
        cls,
        connection: sqlite3.Connection,
        tables: set[str],
    ) -> str | None:
        if "signal_alert_outbox" not in tables:
            return None
        row = connection.execute(
            "SELECT MIN(created_at) FROM signal_alert_outbox WHERE status = 'PENDING'"
        ).fetchone()
        return str(row[0]) if row and row[0] is not None else None
