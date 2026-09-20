from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.identity.user_management import UserManagementError, UserManagementService
from app.application.security.credentials import CredentialService, IssuedCredential
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import User, UserStatus

class InMemoryUserStore:
    def __init__(self, users=None):
        self.users = {u.id: u for u in (users or [])}
    def save(self, user):
        self.users[user.id] = user
    def get(self, user_id):
        return self.users.get(user_id)
    def get_or_create(self, user_id, status):
        return self.users.setdefault(user_id, User(user_id, status))
    def list(self):
        return list(self.users.values())

class InMemoryCredentialStore:
    def __init__(self):
        self.issued = {}
    def create(self, credential, verifier):
        self.issued[credential.id] = credential
    def find_active_user_id(self, secret):
        return None
    def find_active_credential(self, secret):
        return None
    def find_active_for_user(self, user_id):
        return list(self.issued.values())
    def replace(self, credential_id, user_id, replacement, replacement_verifier, revoked_at):
        assert credential_id in self.issued
        self.issued[replacement.id] = replacement
    def revoke(self, credential_id, revoked_at, replacement_id=None):
        pass

class AuditStore:
    def __init__(self):
        self.events=[]
    def append(self, event):
        self.events.append(event)

def make_service(users=None):
    user_store=InMemoryUserStore(users)
    credentials=CredentialService(InMemoryCredentialStore())
    audit=AuditStore()
    return UserManagementService(user_store, credentials, audit), user_store, audit

def test_operator_can_create_user_and_receives_one_time_credential():
    service, users, audit = make_service([User(uuid4(), UserStatus.ACTIVE)])
    user, credential = service.create_user(AuthenticatedIdentity.operator())
    assert user.status is UserStatus.ACTIVE
    assert credential.user_id == user.id
    assert credential.secret
    assert users.get(user.id) == user
    assert audit.events[-1].action == "user_created"

def test_non_operator_cannot_create_user():
    service, _, _ = make_service([User(uuid4(), UserStatus.ACTIVE)])
    with pytest.raises(PermissionError):
        service.create_user(AuthenticatedIdentity.user(uuid4()))

def test_operator_can_disable_and_reactivate_user():
    target=User(uuid4(), UserStatus.ACTIVE)
    service, _, audit = make_service([target])
    actor=AuthenticatedIdentity.operator()
    assert service.set_status(actor, target.id, UserStatus.DISABLED).status is UserStatus.DISABLED
    assert service.set_status(actor, target.id, UserStatus.ACTIVE).status is UserStatus.ACTIVE
    assert [e.action for e in audit.events] == ["user_disabled", "user_active"]

def test_deleted_user_cannot_be_reactivated():
    target=User(uuid4(), UserStatus.DELETED)
    service, _, _ = make_service([target])
    with pytest.raises(UserManagementError, match="Deleted user"):
        service.set_status(AuthenticatedIdentity.operator(), target.id, UserStatus.ACTIVE)

def test_user_can_rotate_own_durable_credential():
    user_id=uuid4()
    target=User(user_id, UserStatus.ACTIVE)
    credential_store=InMemoryCredentialStore()
    credentials=CredentialService(credential_store)
    issued=credentials.provision(user_id)
    service=UserManagementService(InMemoryUserStore([target]), credentials, AuditStore())
    identity=AuthenticatedIdentity.user(user_id, credential_id=issued.id)
    replacement=service.rotate_own_credential(identity)
    assert replacement.user_id == user_id
    assert replacement.secret

def test_legacy_operator_cannot_be_disabled_or_deleted():
    from app.application.security.identity import LEGACY_OPERATOR_USER_ID
    target=User(LEGACY_OPERATOR_USER_ID, UserStatus.ACTIVE)
    service, _, _ = make_service([target])
    with pytest.raises(UserManagementError, match="Legacy operator"):
        service.set_status(AuthenticatedIdentity.operator(), target.id, UserStatus.DISABLED)

def test_operator_can_list_users():
    first=User(uuid4(), UserStatus.ACTIVE)
    service, _, _ = make_service([first])
    users=service.list_users(AuthenticatedIdentity.operator())
    assert first in users
