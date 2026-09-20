from pathlib import Path
from uuid import uuid4

import pytest

from app.application.security.authentication import AuthenticationError
from app.application.security.credentials import CredentialService
from app.application.security.durable_authentication import DurableBearerTokenAuthenticator
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import User, UserStatus
from app.infrastructure.persistence.sqlite_credential_store import SQLiteCredentialStore
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


def make_auth(tmp_path: Path):
    store = SQLiteCredentialStore(tmp_path / "auth.db")
    users = SQLiteUserStore(tmp_path / "auth.db")
    user_id = uuid4()
    users.save(User(user_id, UserStatus.ACTIVE))
    service = CredentialService(store)
    issued = service.provision(user_id)
    return store, users, service, issued


def test_provisioned_credential_authenticates(tmp_path):
    store, users, _, issued = make_auth(tmp_path)
    auth = DurableBearerTokenAuthenticator(store, users)

    identity = auth.authenticate("Bearer " + issued.secret)

    assert identity.user_id == issued.user_id
    assert identity.credential_id == issued.id


def test_invalid_credential_is_rejected(tmp_path):
    store, users, _, _ = make_auth(tmp_path)
    auth = DurableBearerTokenAuthenticator(store, users)

    with pytest.raises(AuthenticationError):
        auth.authenticate("Bearer invalid")


def test_revoked_credential_is_rejected(tmp_path):
    store, users, service, issued = make_auth(tmp_path)
    service.revoke(issued.id)
    auth = DurableBearerTokenAuthenticator(store, users)

    with pytest.raises(AuthenticationError):
        auth.authenticate("Bearer " + issued.secret)


def test_rotation_invalidates_old_credential(tmp_path):
    store, users, service, issued = make_auth(tmp_path)
    replacement = service.rotate(issued.id, issued.user_id)
    auth = DurableBearerTokenAuthenticator(store, users)

    with pytest.raises(AuthenticationError):
        auth.authenticate("Bearer " + issued.secret)

    assert auth.authenticate("Bearer " + replacement.secret).user_id == issued.user_id


def test_disabled_user_cannot_authenticate(tmp_path):
    store, users, service, issued = make_auth(tmp_path)
    users.save(User(issued.user_id, UserStatus.DISABLED))
    auth = DurableBearerTokenAuthenticator(store, users)

    with pytest.raises(AuthenticationError):
        auth.authenticate("Bearer " + issued.secret)


def test_raw_secret_is_not_stored(tmp_path):
    store, users, service, issued = make_auth(tmp_path)
    connection = __import__("sqlite3").connect(tmp_path / "auth.db")
    rows = connection.execute("SELECT verifier FROM user_credentials").fetchall()
    connection.close()

    assert issued.secret not in repr(rows)
    assert issued.secret not in rows[0][0]



def test_rotation_requires_credential_owner(tmp_path):
    store, users, service, issued = make_auth(tmp_path)
    with pytest.raises(ValueError, match="owned by another user"):
        service.rotate(issued.id, uuid4())


def test_m39_fallback_remains_supported(tmp_path):
    from app.application.security.authentication import ConfiguredBearerTokenAuthenticator

    store, users, _, _ = make_auth(tmp_path)
    legacy_user_id = uuid4()
    users.save(User(legacy_user_id, UserStatus.ACTIVE))
    fallback = ConfiguredBearerTokenAuthenticator(
        {"legacy-token": legacy_user_id},
        user_store=users,
    )
    auth = DurableBearerTokenAuthenticator(store, users, fallback=fallback)

    identity = auth.authenticate("Bearer legacy-token")

    assert identity.user_id == legacy_user_id


def test_credential_survives_store_recreation(tmp_path):
    store, users, _, issued = make_auth(tmp_path)
    reloaded_store = SQLiteCredentialStore(tmp_path / "auth.db")
    reloaded_users = SQLiteUserStore(tmp_path / "auth.db")
    auth = DurableBearerTokenAuthenticator(reloaded_store, reloaded_users)

    identity = auth.authenticate("Bearer " + issued.secret)

    assert identity.user_id == issued.user_id
