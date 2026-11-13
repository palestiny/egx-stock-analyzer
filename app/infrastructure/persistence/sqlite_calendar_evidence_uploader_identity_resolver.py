from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.application.market_data.calendar_source_authenticity import (
    CalendarEvidenceUploaderIdentityResolver,
)
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.domain.identity.user import UserStatus
from app.domain.market_data.calendar_evidence import CalendarEvidence
from app.infrastructure.persistence.sqlite_connection import connect_sqlite


class SQLiteCalendarEvidenceUploaderIdentityResolver(CalendarEvidenceUploaderIdentityResolver):
    """Resolve only the evidence's original active, individually granted uploader."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)

    def resolve(self, evidence: CalendarEvidence) -> AuthenticatedIdentity | None:
        credential_id = evidence.recorded_by_credential_id
        if credential_id is None:
            return None
        with connect_sqlite(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT users.id, credentials.id
                FROM users
                JOIN user_credentials AS credentials
                  ON credentials.user_id = users.id
                JOIN operator_access_current AS grants
                  ON grants.user_id = users.id
                WHERE users.id = ?
                  AND users.status = 'active'
                  AND credentials.id = ?
                  AND credentials.status = 'active'
                """,
                (str(evidence.recorded_by), str(credential_id)),
            ).fetchone()
        if row is None:
            return None
        return AuthenticatedIdentity.user(
            UUID(row[0]),
            status=UserStatus.ACTIVE,
            credential_id=UUID(row[1]),
            permissions=frozenset({Permission.OPERATOR}),
        )
