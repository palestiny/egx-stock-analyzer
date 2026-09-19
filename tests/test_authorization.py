import pytest

from app.application.security.authorization import AuthorizationError, OperatorAuthorizer
from app.application.security.identity import AuthenticatedIdentity, Permission


def test_operator_permission_is_accepted():
    OperatorAuthorizer().require(AuthenticatedIdentity.operator(), Permission.OPERATOR)


def test_missing_permission_is_forbidden():
    identity = AuthenticatedIdentity(subject="reader", permissions=frozenset())

    with pytest.raises(AuthorizationError, match="Operator permission"):
        OperatorAuthorizer().require(identity, Permission.OPERATOR)
