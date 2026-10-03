from fastapi import HTTPException

from app.api.authentication import ApiAuthentication
from app.application.security.identity import AuthenticatedIdentity


def test_missing_authentication_configuration_is_not_authenticated_by_default() -> None:
    adapter = ApiAuthentication(
        operator_token=None,
        authenticator=None,
        legacy_test_composition=False,
    )

    try:
        adapter.require_authenticated(None)
    except HTTPException as error:
        assert error.status_code == 503
        assert error.detail == "Authentication is not configured"
    else:
        raise AssertionError("missing authentication configuration must fail closed")


def test_legacy_test_composition_is_explicitly_opt_in() -> None:
    adapter = ApiAuthentication(
        operator_token=None,
        authenticator=None,
        legacy_test_composition=True,
    )

    identity = adapter.require_operator()
    assert identity == AuthenticatedIdentity.operator()
