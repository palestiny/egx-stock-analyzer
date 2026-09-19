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
