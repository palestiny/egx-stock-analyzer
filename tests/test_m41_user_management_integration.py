from pathlib import Path

import pytest

from app.application.identity.user_management import UserManagementService
from app.application.security.authentication import AuthenticationError
from app.application.security.credentials import CredentialService
from app.application.security.durable_authentication import DurableBearerTokenAuthenticator
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import UserStatus
from app.infrastructure.persistence.sqlite_credential_store import SQLiteCredentialStore
from app.infrastructure.persistence.sqlite_management_audit_store import SQLiteManagementAuditStore
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


def make_service(path: Path):
    users = SQLiteUserStore(path)
    credentials = CredentialService(SQLiteCredentialStore(path))
    audit = SQLiteManagementAuditStore(path)
    return UserManagementService(users, credentials, audit), users


def test_user_management_survives_restart_and_rotates_credentials(tmp_path):
    database = tmp_path / "m41.db"
    service, users = make_service(database)

    user, issued = service.create_user(AuthenticatedIdentity.operator())

    reloaded_users = SQLiteUserStore(database)
    reloaded_credentials = SQLiteCredentialStore(database)
    authenticator = DurableBearerTokenAuthenticator(reloaded_credentials, reloaded_users)

    first_identity = authenticator.authenticate("Bearer " + issued.secret)
    assert first_identity.user_id == user.id
    assert first_identity.credential_id == issued.id

    replacement = service.rotate_user_credential(
        AuthenticatedIdentity.operator(),
        user.id,
    )

    with pytest.raises(AuthenticationError):
        authenticator.authenticate("Bearer " + issued.secret)

    second_identity = authenticator.authenticate("Bearer " + replacement.secret)
    assert second_identity.user_id == user.id
    assert second_identity.credential_id == replacement.id


def test_disabled_user_stays_persisted_but_cannot_authenticate(tmp_path):
    database = tmp_path / "m41.db"
    service, users = make_service(database)
    user, issued = service.create_user(AuthenticatedIdentity.operator())

    service.set_status(AuthenticatedIdentity.operator(), user.id, UserStatus.DISABLED)

    reloaded_users = SQLiteUserStore(database)
    reloaded_credentials = SQLiteCredentialStore(database)
    assert reloaded_users.get(user.id).status is UserStatus.DISABLED

    authenticator = DurableBearerTokenAuthenticator(reloaded_credentials, reloaded_users)
    with pytest.raises(AuthenticationError):
        authenticator.authenticate("Bearer " + issued.secret)
