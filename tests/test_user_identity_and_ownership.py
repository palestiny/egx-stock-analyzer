from uuid import UUID

import pytest

from app.application.security.authorization import AuthorizationError, OwnershipAuthorizer
from app.application.security.identity import (
    LEGACY_OPERATOR_USER_ID,
    AuthenticatedIdentity,
)
from app.domain.identity.user import UserStatus


USER_A = UUID("00000000-0000-0000-0000-00000000000a")
USER_B = UUID("00000000-0000-0000-0000-00000000000b")


def test_user_identity_has_stable_internal_uuid():
    identity = AuthenticatedIdentity.user(USER_A)

    assert identity.user_id == USER_A
    assert identity.user_status is UserStatus.ACTIVE


def test_user_can_access_owned_resource():
    authorizer = OwnershipAuthorizer()
    identity = AuthenticatedIdentity.user(USER_A)

    authorizer.require_owner(identity, USER_A)


def test_user_cannot_access_another_users_resource():
    authorizer = OwnershipAuthorizer()
    identity = AuthenticatedIdentity.user(USER_A)

    with pytest.raises(AuthorizationError, match="another user"):
        authorizer.require_owner(identity, USER_B)


@pytest.mark.parametrize("status", [UserStatus.DISABLED, UserStatus.DELETED])
def test_inactive_user_cannot_access_protected_resource(status):
    authorizer = OwnershipAuthorizer()
    identity = AuthenticatedIdentity.user(USER_A, status=status)

    with pytest.raises(AuthorizationError, match="not active"):
        authorizer.require_owner(identity, USER_A)


def test_global_access_requires_active_authenticated_identity():
    authorizer = OwnershipAuthorizer()

    authorizer.require_global_access(AuthenticatedIdentity.user(USER_A))

    with pytest.raises(AuthorizationError, match="not active"):
        authorizer.require_global_access(
            AuthenticatedIdentity.user(USER_A, status=UserStatus.DISABLED)
        )


def test_m37_operator_identity_maps_to_stable_legacy_user():
    identity = AuthenticatedIdentity.operator()

    assert identity.user_id == LEGACY_OPERATOR_USER_ID
    assert identity.user_status is UserStatus.ACTIVE
