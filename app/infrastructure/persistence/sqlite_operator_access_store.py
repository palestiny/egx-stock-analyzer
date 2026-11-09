from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.application.security.operator_access import OperatorAccessEvent
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteOperatorAccessStore:
    """Current operator grants plus append-only, attributable grant/revoke history."""

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
                CREATE TABLE IF NOT EXISTS operator_access_current (
                    user_id TEXT PRIMARY KEY REFERENCES users(id),
                    granted_at TEXT NOT NULL,
                    reason TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operator_access_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL CHECK (action IN ('BOOTSTRAP', 'GRANT', 'REVOKE')),
                    target_user_id TEXT NOT NULL REFERENCES users(id),
                    actor_user_id TEXT NULL REFERENCES users(id),
                    actor_credential_id TEXT NULL,
                    actor_kind TEXT NOT NULL CHECK (actor_kind IN ('SYSTEM_BOOTSTRAP', 'INDIVIDUAL_OPERATOR')),
                    reason TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    CHECK (
                        (actor_kind = 'SYSTEM_BOOTSTRAP' AND actor_user_id IS NULL AND actor_credential_id IS NULL AND action = 'BOOTSTRAP')
                        OR
                        (actor_kind = 'INDIVIDUAL_OPERATOR' AND actor_user_id IS NOT NULL AND actor_credential_id IS NOT NULL AND action IN ('GRANT', 'REVOKE'))
                    )
                );

                CREATE TRIGGER IF NOT EXISTS operator_access_prevent_last_operator_disable
                BEFORE UPDATE OF status ON users
                WHEN OLD.status = 'active'
                 AND NEW.status <> 'active'
                 AND EXISTS (
                     SELECT 1 FROM operator_access_current WHERE user_id = OLD.id
                 )
                 AND (
                     SELECT COUNT(*)
                     FROM operator_access_current AS g
                     JOIN users AS u ON u.id = g.user_id
                     WHERE u.status = 'active'
                 ) <= 1
                BEGIN
                    SELECT RAISE(ABORT, 'cannot disable the last active operator');
                END;

                CREATE TRIGGER IF NOT EXISTS operator_access_events_no_update
                BEFORE UPDATE ON operator_access_events
                BEGIN
                    SELECT RAISE(ABORT, 'operator access events are immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS operator_access_events_no_delete
                BEFORE DELETE ON operator_access_events
                BEGIN
                    SELECT RAISE(ABORT, 'operator access events are immutable');
                END;
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _require_reason(reason: str) -> str:
        normalized = reason.strip()
        if not normalized or len(normalized) > 500:
            raise ValueError("A reason between 1 and 500 characters is required")
        return normalized

    @staticmethod
    def _require_active_user(connection: sqlite3.Connection, user_id: UUID) -> None:
        row = connection.execute(
            "SELECT status FROM users WHERE id = ?", (str(user_id),)
        ).fetchone()
        if row is None or row[0] != "active":
            raise ValueError("Operator target must be an active user")

        credential = connection.execute(
            "SELECT 1 FROM user_credentials WHERE user_id = ? AND status = 'active' LIMIT 1",
            (str(user_id),),
        ).fetchone()
        if credential is None:
            raise ValueError("Operator target must have an active durable credential")

    @staticmethod
    def _require_actor(
        connection: sqlite3.Connection,
        actor_user_id: UUID,
        actor_credential_id: UUID,
    ) -> None:
        row = connection.execute(
            """
            SELECT 1
            FROM operator_access_current AS grant_row
            JOIN users AS u ON u.id = grant_row.user_id
            JOIN user_credentials AS c ON c.user_id = u.id
            WHERE grant_row.user_id = ?
              AND u.status = 'active'
              AND c.id = ?
              AND c.status = 'active'
            """,
            (str(actor_user_id), str(actor_credential_id)),
        ).fetchone()
        if row is None:
            raise ValueError("Actor is not an active operator using an active durable credential")

    def is_operator(self, user_id: UUID) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM operator_access_current AS g
                JOIN users AS u ON u.id = g.user_id
                WHERE g.user_id = ? AND u.status = 'active'
                """,
                (str(user_id),),
            ).fetchone()
        return row is not None

    def bootstrap_first_operator(self, target_user_id: UUID, *, reason: str) -> None:
        normalized_reason = self._require_reason(reason)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute(
                """
                SELECT COUNT(*) FROM operator_access_current AS g
                JOIN users AS u ON u.id = g.user_id
                WHERE u.status = 'active'
                """
            ).fetchone()[0]
            if count:
                raise ValueError("First operator bootstrap is only allowed when no operator exists")
            self._require_active_user(connection, target_user_id)
            now = self._now()
            connection.execute(
                "INSERT INTO operator_access_current (user_id, granted_at, reason) VALUES (?, ?, ?)",
                (str(target_user_id), now, normalized_reason),
            )
            connection.execute(
                """
                INSERT INTO operator_access_events
                    (action, target_user_id, actor_user_id, actor_credential_id, actor_kind, reason, occurred_at)
                VALUES ('BOOTSTRAP', ?, NULL, NULL, 'SYSTEM_BOOTSTRAP', ?, ?)
                """,
                (str(target_user_id), normalized_reason, now),
            )

    def grant(
        self,
        target_user_id: UUID,
        *,
        actor_user_id: UUID,
        actor_credential_id: UUID,
        reason: str,
    ) -> None:
        normalized_reason = self._require_reason(reason)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require_actor(connection, actor_user_id, actor_credential_id)
            self._require_active_user(connection, target_user_id)
            existing = connection.execute(
                "SELECT 1 FROM operator_access_current WHERE user_id = ?",
                (str(target_user_id),),
            ).fetchone()
            if existing:
                raise ValueError("User is already an operator")
            now = self._now()
            connection.execute(
                "INSERT INTO operator_access_current (user_id, granted_at, reason) VALUES (?, ?, ?)",
                (str(target_user_id), now, normalized_reason),
            )
            connection.execute(
                """
                INSERT INTO operator_access_events
                    (action, target_user_id, actor_user_id, actor_credential_id, actor_kind, reason, occurred_at)
                VALUES ('GRANT', ?, ?, ?, 'INDIVIDUAL_OPERATOR', ?, ?)
                """,
                (str(target_user_id), str(actor_user_id), str(actor_credential_id), normalized_reason, now),
            )

    def revoke(
        self,
        target_user_id: UUID,
        *,
        actor_user_id: UUID,
        actor_credential_id: UUID,
        reason: str,
    ) -> None:
        normalized_reason = self._require_reason(reason)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require_actor(connection, actor_user_id, actor_credential_id)
            existing = connection.execute(
                "SELECT 1 FROM operator_access_current WHERE user_id = ?",
                (str(target_user_id),),
            ).fetchone()
            if existing is None:
                raise ValueError("User is not an active operator")
            count = connection.execute(
                """
                SELECT COUNT(*) FROM operator_access_current AS g
                JOIN users AS u ON u.id = g.user_id
                WHERE u.status = 'active'
                """
            ).fetchone()[0]
            if count <= 1:
                raise ValueError("Cannot revoke the last active operator")
            now = self._now()
            connection.execute(
                "DELETE FROM operator_access_current WHERE user_id = ?",
                (str(target_user_id),),
            )
            connection.execute(
                """
                INSERT INTO operator_access_events
                    (action, target_user_id, actor_user_id, actor_credential_id, actor_kind, reason, occurred_at)
                VALUES ('REVOKE', ?, ?, ?, 'INDIVIDUAL_OPERATOR', ?, ?)
                """,
                (str(target_user_id), str(actor_user_id), str(actor_credential_id), normalized_reason, now),
            )

    def list_events(self) -> tuple[OperatorAccessEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, action, target_user_id, actor_user_id, actor_credential_id,
                       actor_kind, reason, occurred_at
                FROM operator_access_events ORDER BY id ASC
                """
            ).fetchall()
        return tuple(
            OperatorAccessEvent(
                event_id=row[0],
                action=row[1],
                target_user_id=UUID(row[2]),
                actor_user_id=UUID(row[3]) if row[3] else None,
                actor_credential_id=UUID(row[4]) if row[4] else None,
                actor_kind=row[5],
                reason=row[6],
                occurred_at=datetime.fromisoformat(row[7]),
            )
            for row in rows
        )
