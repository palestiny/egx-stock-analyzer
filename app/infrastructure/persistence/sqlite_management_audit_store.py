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
