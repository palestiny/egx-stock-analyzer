import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.application.identity.management_audit import ManagementAuditEvent, ManagementAuditStore

class SQLiteManagementAuditStore(ManagementAuditStore):
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS management_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_user_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    outcome TEXT NOT NULL
                )
                """
            )

    def append(self, event: ManagementAuditEvent) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO management_audit
                    (actor_user_id, action, target_user_id, occurred_at, outcome)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(event.actor_user_id),
                    event.action,
                    str(event.target_user_id),
                    event.occurred_at.isoformat(),
                    event.outcome,
                ),
            )

    def list_events(self) -> list[ManagementAuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT actor_user_id, action, target_user_id, occurred_at, outcome
                FROM management_audit
                ORDER BY id ASC
                """
            ).fetchall()
        return [
            ManagementAuditEvent(
                actor_user_id=UUID(row[0]),
                action=row[1],
                target_user_id=UUID(row[2]),
                occurred_at=datetime.fromisoformat(row[3]),
                outcome=row[4],
            )
            for row in rows
        ]

    def read_page(
        self,
        query,
        *,
        offset: int,
        limit: int,
    ):
        clauses = []
        parameters = []

        if query.actor_user_id is not None:
            clauses.append("actor_user_id = ?")
            parameters.append(str(query.actor_user_id))
        if query.target_user_id is not None:
            clauses.append("target_user_id = ?")
            parameters.append(str(query.target_user_id))
        if query.action is not None:
            clauses.append("action = ?")
            parameters.append(query.action)
        elif query.actions:
            placeholders = ", ".join("?" for _ in query.actions)
            clauses.append(f"action IN ({placeholders})")
            parameters.extend(query.actions)
        if query.outcome is not None:
            clauses.append("outcome = ?")
            parameters.append(query.outcome)
        if query.from_time is not None:
            clauses.append("occurred_at >= ?")
            parameters.append(query.from_time.isoformat())
        if query.to_time is not None:
            clauses.append("occurred_at < ?")
            parameters.append(query.to_time.isoformat())

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._connect() as connection:
            total_count = connection.execute(
                f"SELECT COUNT(*) FROM management_audit{where}",
                parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT id, actor_user_id, action, target_user_id, occurred_at, outcome
                FROM management_audit
                {where}
                ORDER BY occurred_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*parameters, limit, offset],
            ).fetchall()

        from app.application.identity.management_audit import (
            ManagementAuditEvent,
            ManagementAuditPage,
            ManagementAuditRecord,
        )

        items = tuple(
            ManagementAuditRecord(
                audit_id=row[0],
                event=ManagementAuditEvent(
                    actor_user_id=UUID(row[1]),
                    action=row[2],
                    target_user_id=UUID(row[3]),
                    occurred_at=datetime.fromisoformat(row[4]),
                    outcome=row[5],
                ),
            )
            for row in rows
        )
        return ManagementAuditPage(
            items=items,
            total_count=total_count,
            has_more=offset + len(items) < total_count,
        )
