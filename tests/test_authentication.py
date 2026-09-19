import pytest

from app.application.security.authentication import (
    AuthenticationError,
    BearerTokenAuthenticator,
)
from app.application.security.identity import Permission


def test_valid_bearer_token_authenticates_operator():
    identity = BearerTokenAuthenticator("secret-token").authenticate("Bearer secret-token")

    assert identity.subject == "operator"
    assert identity.permissions == frozenset({Permission.OPERATOR})


@pytest.mark.parametrize("header", [None, "", "Basic secret-token", "Bearer", "Bearer wrong"])
def test_invalid_bearer_credentials_are_rejected(header):
    with pytest.raises(AuthenticationError, match="Authentication"):
        BearerTokenAuthenticator("secret-token").authenticate(header)


def test_authenticator_never_returns_the_token():
    identity = BearerTokenAuthenticator("secret-token").authenticate("Bearer secret-token")

    assert "secret-token" not in repr(identity)
