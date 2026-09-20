import pytest

from app.application.security.authorization import AuthorizationError, OperatorAuthorizer
from app.application.security.identity import AuthenticatedIdentity, Permission


def test_operator_identity_has_operator_permission():
    identity = AuthenticatedIdentity.operator()

    OperatorAuthorizer().require(identity, Permission.OPERATOR)


def test_identity_without_required_permission_is_rejected():
    identity = AuthenticatedIdentity(
        subject="future-user",
        permissions=frozenset(),
    )

    with pytest.raises(AuthorizationError, match="Operator permission is required"):
        OperatorAuthorizer().require(identity, Permission.OPERATOR)


from uuid import uuid4

from app.application.security.authorization import OwnershipAuthorizer


def test_owner_or_global_allows_matching_owner():
    user_id = uuid4()

    OwnershipAuthorizer().require_owner_or_global(
        AuthenticatedIdentity.user(user_id),
        user_id,
    )


def test_owner_or_global_rejects_non_owner():
    with pytest.raises(AuthorizationError, match="another user"):
        OwnershipAuthorizer().require_owner_or_global(
            AuthenticatedIdentity.user(uuid4()),
            uuid4(),
        )


def test_owner_or_global_requires_operator_for_global_resource():
    with pytest.raises(AuthorizationError, match="Operator permission"):
        OwnershipAuthorizer().require_owner_or_global(
            AuthenticatedIdentity.user(uuid4()),
            None,
        )


def test_owner_or_global_allows_legacy_operator_for_global_resource():
    OwnershipAuthorizer().require_owner_or_global(
        AuthenticatedIdentity.operator(),
        None,
    )
