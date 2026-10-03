import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.identity.user_management import UserManagementService
from app.application.security.credentials import CredentialService
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import User, UserStatus
from app.infrastructure.persistence.sqlite_credential_store import SQLiteCredentialStore
from app.infrastructure.persistence.sqlite_management_audit_store import SQLiteManagementAuditStore
from app.infrastructure.persistence.sqlite_management_mutation_transaction import SQLiteManagementMutationTransaction
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


def make_service(path: Path, *, fail_audit: bool = False):
    users = SQLiteUserStore(path)
    credential_store = SQLiteCredentialStore(path)
    credentials = CredentialService(credential_store)
    audit = SQLiteManagementAuditStore(path)
    transaction = SQLiteManagementMutationTransaction(
        path,
        audit_failure_hook=(lambda: (_ for _ in ()).throw(RuntimeError("audit write failed"))) if fail_audit else None,
    )
    return UserManagementService(users, credentials, audit, transaction), users, credential_store, audit


def test_create_user_rolls_back_user_and_credential_when_audit_fails(tmp_path):
    database = tmp_path / "atomic-create.db"
    service, users, credentials, audit = make_service(database, fail_audit=True)

    with pytest.raises(RuntimeError, match="audit write failed"):
        service.create_user(AuthenticatedIdentity.operator())

    assert users.list() == []
    assert credentials.find_active_for_user(uuid4()) == []
    assert audit.list_events() == []

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM user_credentials").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM management_audit").fetchone()[0] == 0


def test_status_change_rolls_back_when_audit_fails(tmp_path):
    database = tmp_path / "atomic-status.db"
    service, users, _, audit = make_service(database)
    user = User(uuid4(), UserStatus.ACTIVE)
    users.save(user)

    failing, _, _, _ = make_service(database, fail_audit=True)
    with pytest.raises(RuntimeError, match="audit write failed"):
        failing.set_status(AuthenticatedIdentity.operator(), user.id, UserStatus.DISABLED)

    assert users.get(user.id).status is UserStatus.ACTIVE
    assert audit.list_events() == []


def test_credential_rotation_rolls_back_when_audit_fails(tmp_path):
    database = tmp_path / "atomic-rotation.db"
    service, users, credentials, audit = make_service(database)
    user = User(uuid4(), UserStatus.ACTIVE)
    users.save(user)
    original = CredentialService(credentials)
    issued = original.provision(user.id)

    failing, _, _, _ = make_service(database, fail_audit=True)
    with pytest.raises(RuntimeError, match="audit write failed"):
        failing.rotate_user_credential(AuthenticatedIdentity.operator(), user.id)

    active = credentials.find_active_for_user(user.id)
    assert [item.id for item in active] == [issued.id]
    assert audit.list_events() == []
