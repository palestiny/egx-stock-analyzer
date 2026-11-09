from uuid import uuid4

import pytest

from app.application.security.credentials import CredentialService
from app.domain.identity.user import User, UserStatus
from app.infrastructure.operator_access_bootstrap import bootstrap_first_operator
from app.infrastructure.persistence.sqlite_credential_store import SQLiteCredentialStore
from app.infrastructure.persistence.sqlite_operator_access_store import SQLiteOperatorAccessStore
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


def setup_operator_database(path):
    users = SQLiteUserStore(path)
    credentials = SQLiteCredentialStore(path)
    access = SQLiteOperatorAccessStore(path)
    first_user, second_user = uuid4(), uuid4()
    users.save(User(first_user, UserStatus.ACTIVE))
    users.save(User(second_user, UserStatus.ACTIVE))
    service = CredentialService(credentials)
    first_credential = service.provision(first_user)
    second_credential = service.provision(second_user)
    return users, credentials, access, first_user, second_user, first_credential, second_credential


def test_bootstrap_requires_empty_operator_set_and_active_durable_credential(tmp_path):
    path = tmp_path / "operators.db"
    _, _, access, first, second, _, _ = setup_operator_database(path)

    access.bootstrap_first_operator(first, reason="Initial owner setup")
    assert access.is_operator(first)
    with pytest.raises(ValueError, match="only allowed when no operator exists"):
        access.bootstrap_first_operator(second, reason="Second bootstrap")


def test_bootstrap_rejects_user_without_active_credential(tmp_path):
    path = tmp_path / "operators.db"
    users = SQLiteUserStore(path)
    access = SQLiteOperatorAccessStore(path)
    target = uuid4()
    users.save(User(target, UserStatus.ACTIVE))
    with pytest.raises(ValueError, match="active durable credential"):
        access.bootstrap_first_operator(target, reason="Initial setup")


def test_grant_and_revoke_are_attributed_and_preserve_append_only_history(tmp_path):
    path = tmp_path / "operators.db"
    _, _, access, first, second, first_credential, _ = setup_operator_database(path)
    access.bootstrap_first_operator(first, reason="Initial owner setup")

    access.grant(
        second,
        actor_user_id=first,
        actor_credential_id=first_credential.id,
        reason="Operations coverage",
    )
    assert access.is_operator(second)
    access.revoke(
        second,
        actor_user_id=first,
        actor_credential_id=first_credential.id,
        reason="Role no longer required",
    )
    assert not access.is_operator(second)

    events = access.list_events()
    assert [event.action for event in events] == ["BOOTSTRAP", "GRANT", "REVOKE"]
    assert events[0].actor_kind == "SYSTEM_BOOTSTRAP"
    assert events[1].actor_user_id == first
    assert events[1].actor_credential_id == first_credential.id


def test_last_active_operator_cannot_be_revoked(tmp_path):
    path = tmp_path / "operators.db"
    _, _, access, first, _, first_credential, _ = setup_operator_database(path)
    access.bootstrap_first_operator(first, reason="Initial owner setup")

    with pytest.raises(ValueError, match="last active operator"):
        access.revoke(
            first,
            actor_user_id=first,
            actor_credential_id=first_credential.id,
            reason="Attempted self removal",
        )
    assert access.is_operator(first)


def test_grant_requires_active_operator_and_active_credential(tmp_path):
    path = tmp_path / "operators.db"
    users, credentials, access, first, second, first_credential, _ = setup_operator_database(path)
    access.bootstrap_first_operator(first, reason="Initial owner setup")
    replacement = CredentialService(credentials).rotate(first_credential.id, first)

    with pytest.raises(ValueError, match="active durable credential"):
        access.grant(
            second,
            actor_user_id=first,
            actor_credential_id=first_credential.id,
            reason="Stale credential",
        )
    access.grant(
        second,
        actor_user_id=first,
        actor_credential_id=replacement.id,
        reason="Current credential",
    )


def test_disabled_user_loses_operator_authority_and_cannot_be_granted(tmp_path):
    path = tmp_path / "operators.db"
    users, _, access, first, second, first_credential, _ = setup_operator_database(path)
    access.bootstrap_first_operator(first, reason="Initial owner setup")
    users.save(User(first, UserStatus.DISABLED))
    assert not access.is_operator(first)
    with pytest.raises(ValueError, match="active user"):
        access.grant(
            second,
            actor_user_id=first,
            actor_credential_id=first_credential.id,
            reason="Disabled actor",
        )


def test_operator_events_reject_update_and_delete(tmp_path):
    path = tmp_path / "operators.db"
    _, _, access, first, _, _, _ = setup_operator_database(path)
    access.bootstrap_first_operator(first, reason="Initial owner setup")
    import sqlite3

    connection = sqlite3.connect(path)
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute("UPDATE operator_access_events SET reason = 'changed'")
    connection.rollback()
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute("DELETE FROM operator_access_events")
    connection.close()


def test_bootstrap_cli_helper_requires_existing_user_and_active_credential(tmp_path):
    path = tmp_path / "operators.db"
    users = SQLiteUserStore(path)
    target = uuid4()
    users.save(User(target, UserStatus.ACTIVE))
    with pytest.raises(ValueError, match="active durable credential"):
        bootstrap_first_operator(str(path), target, "Local setup")


def test_last_operator_cannot_be_disabled_or_deleted(tmp_path):
    path = tmp_path / "operators.db"
    users, _, access, first, _, _, _ = setup_operator_database(path)
    access.bootstrap_first_operator(first, reason="Initial owner setup")

    with pytest.raises(Exception, match="last active operator"):
        users.save(User(first, UserStatus.DISABLED))
    assert access.is_operator(first)
