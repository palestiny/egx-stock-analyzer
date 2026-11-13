from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.application.market_data.calendar_source_authenticity import (
    TrustedCalendarSourceOrigin,
    normalize_calendar_source_origin,
)
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteCalendarSourceOriginRegistry:
    """Append-only exact-origin trust decisions restricted to the configured owner."""

    def __init__(self, database_path: str | Path, *, owner_user_id: UUID) -> None:
        path = Path(database_path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._owner_user_id = owner_user_id
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = connect_sqlite(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS egx_calendar_source_origin_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL CHECK (action IN ('APPROVE', 'REVOKE')),
                    origin TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    source_class TEXT NOT NULL CHECK (source_class IN ('A', 'A-R')),
                    market_scope TEXT NOT NULL,
                    trust_basis TEXT NOT NULL,
                    registry_version TEXT NOT NULL,
                    actor_user_id TEXT NOT NULL REFERENCES users(id),
                    actor_credential_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_calendar_source_origin_events_latest
                ON egx_calendar_source_origin_events(origin, event_id);

                CREATE TRIGGER IF NOT EXISTS egx_calendar_source_origin_events_no_update
                BEFORE UPDATE ON egx_calendar_source_origin_events
                BEGIN
                    SELECT RAISE(ABORT, 'calendar source origin events are immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS egx_calendar_source_origin_events_no_delete
                BEFORE DELETE ON egx_calendar_source_origin_events
                BEGIN
                    SELECT RAISE(ABORT, 'calendar source origin events are immutable');
                END;
                """
            )

    def approve_origin(
        self,
        origin: str,
        *,
        publisher: str,
        source_class: str,
        market_scope: str,
        trust_basis: str,
        registry_version: str,
        owner: AuthenticatedIdentity,
        occurred_at: datetime | None = None,
    ) -> TrustedCalendarSourceOrigin:
        self._require_owner(owner)
        assert owner.user_id is not None and owner.credential_id is not None
        canonical_origin = normalize_calendar_source_origin(origin)
        for name, value in (
            ("publisher", publisher),
            ("source_class", source_class),
            ("market_scope", market_scope),
            ("trust_basis", trust_basis),
            ("registry_version", registry_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if source_class not in {"A", "A-R"}:
            raise ValueError("Only primary source classes A and A-R may be origin-trusted")
        timestamp = occurred_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Origin approval timestamp must be timezone-aware")
        timestamp = timestamp.astimezone(timezone.utc)
        if source_class == "A" and publisher != "EGX":
            raise ValueError("Class A origin approval requires EGX publisher identity")
        if source_class == "A-R" and (publisher != "FRA" or market_scope != "FRA_REGULATORY"):
            raise ValueError("Class A-R origin approval is restricted to FRA regulatory scope")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require_active_owner_credential(connection, owner)
            if connection.execute(
                "SELECT 1 FROM egx_calendar_source_origin_events WHERE origin = ? AND registry_version = ? LIMIT 1",
                (canonical_origin, registry_version.strip()),
            ).fetchone() is not None:
                raise ValueError("Registry version must be unique for each origin trust event")
            latest = connection.execute(
                "SELECT action, occurred_at FROM egx_calendar_source_origin_events WHERE origin = ? ORDER BY event_id DESC LIMIT 1",
                (canonical_origin,),
            ).fetchone()
            if latest is not None:
                if latest[0] == "APPROVE":
                    raise ValueError("Origin is already approved; revoke it before creating a new approval")
                if timestamp < datetime.fromisoformat(latest[1]):
                    raise ValueError("Origin approval time cannot precede the latest trust event")
            connection.execute(
                """
                INSERT INTO egx_calendar_source_origin_events (
                    action, origin, publisher, source_class, market_scope,
                    trust_basis, registry_version, actor_user_id,
                    actor_credential_id, occurred_at
                ) VALUES ('APPROVE', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    canonical_origin, publisher, source_class, market_scope,
                    trust_basis.strip(), registry_version.strip(),
                    str(owner.user_id), str(owner.credential_id), timestamp.isoformat(),
                ),
            )
        return TrustedCalendarSourceOrigin(
            origin=canonical_origin,
            publisher=publisher,
            source_class=source_class,
            market_scope=market_scope,
            trust_basis=trust_basis.strip(),
            registry_version=registry_version.strip(),
            approved_by=owner.user_id,
            approved_by_credential_id=owner.credential_id,
            approved_at=timestamp,
        )

    def revoke_origin(
        self,
        origin: str,
        *,
        reason: str,
        registry_version: str,
        owner: AuthenticatedIdentity,
        occurred_at: datetime | None = None,
    ) -> None:
        self._require_owner(owner)
        assert owner.user_id is not None and owner.credential_id is not None
        canonical_origin = normalize_calendar_source_origin(origin)
        if not reason.strip() or not registry_version.strip():
            raise ValueError("Revocation reason and registry version are required")
        timestamp = occurred_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Origin revocation timestamp must be timezone-aware")
        timestamp = timestamp.astimezone(timezone.utc)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require_active_owner_credential(connection, owner)
            if connection.execute(
                "SELECT 1 FROM egx_calendar_source_origin_events WHERE origin = ? AND registry_version = ? LIMIT 1",
                (canonical_origin, registry_version.strip()),
            ).fetchone() is not None:
                raise ValueError("Registry version must be unique for each origin trust event")
            latest_event = connection.execute(
                "SELECT action, occurred_at FROM egx_calendar_source_origin_events WHERE origin = ? ORDER BY event_id DESC LIMIT 1",
                (canonical_origin,),
            ).fetchone()
            if latest_event is not None and timestamp < datetime.fromisoformat(latest_event[1]):
                raise ValueError("Origin revocation time cannot precede the latest trust event")
            current = connection.execute(
                """
                SELECT publisher, source_class, market_scope, trust_basis
                FROM egx_calendar_source_origin_events
                WHERE origin = ? AND action = 'APPROVE'
                ORDER BY event_id DESC LIMIT 1
                """,
                (canonical_origin,),
            ).fetchone()
            if current is None:
                raise ValueError("Cannot revoke an origin that has never been approved")
            latest = connection.execute(
                "SELECT action FROM egx_calendar_source_origin_events WHERE origin = ? ORDER BY event_id DESC LIMIT 1",
                (canonical_origin,),
            ).fetchone()
            if latest is None or latest[0] != "APPROVE":
                raise ValueError("Origin is not currently approved")
            connection.execute(
                """
                INSERT INTO egx_calendar_source_origin_events (
                    action, origin, publisher, source_class, market_scope,
                    trust_basis, registry_version, actor_user_id,
                    actor_credential_id, occurred_at
                ) VALUES ('REVOKE', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    canonical_origin, current[0], current[1], current[2],
                    f"Revoked: {reason.strip()}", registry_version.strip(),
                    str(owner.user_id), str(owner.credential_id), timestamp.isoformat(),
                ),
            )

    def get_exact_origin(
        self, origin: str, *, at: datetime
    ) -> TrustedCalendarSourceOrigin | None:
        canonical_origin = normalize_calendar_source_origin(origin)
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("Origin lookup timestamp must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT action, origin, publisher, source_class, market_scope,
                       trust_basis, registry_version, actor_user_id,
                       actor_credential_id, occurred_at
                FROM egx_calendar_source_origin_events
                WHERE origin = ? AND occurred_at <= ?
                ORDER BY event_id DESC LIMIT 1
                """,
                (canonical_origin, at.astimezone(timezone.utc).isoformat()),
            ).fetchone()
        if row is None or row[0] != "APPROVE":
            return None
        return TrustedCalendarSourceOrigin(
            origin=row[1],
            publisher=row[2],
            source_class=row[3],
            market_scope=row[4],
            trust_basis=row[5],
            registry_version=row[6],
            approved_by=UUID(row[7]),
            approved_by_credential_id=UUID(row[8]),
            approved_at=datetime.fromisoformat(row[9]),
        )

    def assert_configured_owner(self, identity: AuthenticatedIdentity) -> None:
        self._require_owner(identity)
        with self._connect() as connection:
            self._require_active_owner_credential(connection, identity)

    def list_events(self) -> tuple[dict[str, object], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, action, origin, publisher, source_class,
                       market_scope, trust_basis, registry_version,
                       actor_user_id, actor_credential_id, occurred_at
                FROM egx_calendar_source_origin_events ORDER BY event_id
                """
            ).fetchall()
        return tuple({
            "event_id": row[0], "action": row[1], "origin": row[2],
            "publisher": row[3], "source_class": row[4],
            "market_scope": row[5], "trust_basis": row[6],
            "registry_version": row[7], "actor_user_id": UUID(row[8]),
            "actor_credential_id": UUID(row[9]),
            "occurred_at": datetime.fromisoformat(row[10]),
        } for row in rows)

    def _require_owner(self, identity: AuthenticatedIdentity) -> None:
        if (
            identity.user_id != self._owner_user_id
            or identity.credential_id is None
            or identity.subject != str(identity.user_id)
            or Permission.OPERATOR not in identity.permissions
        ):
            raise PermissionError("Only the configured owner using an individual operator credential may change origin trust")

    @staticmethod
    def _require_active_owner_credential(
        connection: sqlite3.Connection, identity: AuthenticatedIdentity
    ) -> None:
        row = connection.execute(
            """
            SELECT 1
            FROM users u
            JOIN user_credentials c ON c.user_id = u.id
            JOIN operator_access_current g ON g.user_id = u.id
            WHERE u.id = ? AND u.status = 'active'
              AND c.id = ? AND c.status = 'active'
            """,
            (str(identity.user_id), str(identity.credential_id)),
        ).fetchone()
        if row is None:
            raise PermissionError("Owner must use an active durable credential")
