from uuid import uuid4

import pytest

from app.application.security.authentication import (
    AuthenticationError,
    ConfiguredBearerTokenAuthenticator,
)
from app.application.security.identity import LEGACY_OPERATOR_USER_ID, Permission
from app.domain.identity.user import User, UserStatus


class InMemoryUserStore:
    def __init__(self, users: list[User]) -> None:
        self._users = {user.id: user for user in users}
        self.lookups = []

    def get(self, user_id):
        self.lookups.append(user_id)
        return self._users.get(user_id)


def test_user_bearer_token_resolves_to_active_user():
    user_id = uuid4()
    store = InMemoryUserStore([User(user_id, UserStatus.ACTIVE)])
    authenticator = ConfiguredBearerTokenAuthenticator(
        {"user-token": user_id},
        user_store=store,
    )

    identity = authenticator.authenticate("Bearer user-token")

    assert identity.user_id == user_id
    assert identity.subject == str(user_id)
    assert identity.permissions == frozenset()
    assert identity.user_status is UserStatus.ACTIVE
    assert store.lookups == [user_id]


@pytest.mark.parametrize("status", [UserStatus.DISABLED, UserStatus.DELETED])
def test_inactive_user_cannot_authenticate(status):
    user_id = uuid4()
    store = InMemoryUserStore([User(user_id, status)])
    authenticator = ConfiguredBearerTokenAuthenticator(
        {"user-token": user_id},
        user_store=store,
    )

    with pytest.raises(AuthenticationError, match="Authentication"):
        authenticator.authenticate("Bearer user-token")


def test_missing_mapped_user_cannot_authenticate():
    user_id = uuid4()
    store = InMemoryUserStore([])
    authenticator = ConfiguredBearerTokenAuthenticator(
        {"user-token": user_id},
        user_store=store,
    )

    with pytest.raises(AuthenticationError, match="Authentication"):
        authenticator.authenticate("Bearer user-token")


def test_legacy_operator_token_resolves_only_to_legacy_operator_identity():
    store = InMemoryUserStore([User(LEGACY_OPERATOR_USER_ID, UserStatus.ACTIVE)])
    authenticator = ConfiguredBearerTokenAuthenticator(
        {},
        user_store=store,
        legacy_operator_token="legacy-token",
    )

    identity = authenticator.authenticate("Bearer legacy-token")

    assert identity.user_id == LEGACY_OPERATOR_USER_ID
    assert identity.permissions == frozenset({Permission.OPERATOR})


def test_invalid_credentials_are_rejected():
    user_id = uuid4()
    store = InMemoryUserStore([User(user_id, UserStatus.ACTIVE)])
    authenticator = ConfiguredBearerTokenAuthenticator(
        {"user-token": user_id},
        user_store=store,
        legacy_operator_token="legacy-token",
    )

    for header in (None, "", "Basic user-token", "Bearer wrong"):
        with pytest.raises(AuthenticationError):
            authenticator.authenticate(header)


def test_authenticator_never_returns_raw_credentials():
    user_id = uuid4()
    store = InMemoryUserStore([User(user_id, UserStatus.ACTIVE)])
    authenticator = ConfiguredBearerTokenAuthenticator(
        {"super-secret": user_id},
        user_store=store,
    )

    identity = authenticator.authenticate("Bearer super-secret")

    assert "super-secret" not in repr(identity)
