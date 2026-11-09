from uuid import uuid4

import pytest

from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.security.operator_access import OperatorAccessError, OperatorAccessService


class FakeOperatorAccessStore:
    def __init__(self):
        self.events = []
        self.grants = set()

    def is_operator(self, user_id):
        return user_id in self.grants

    def grant(self, target_user_id, *, actor_user_id, actor_credential_id, reason):
        self.events.append(("GRANT", target_user_id, actor_user_id, actor_credential_id, reason))
        self.grants.add(target_user_id)

    def revoke(self, target_user_id, *, actor_user_id, actor_credential_id, reason):
        self.events.append(("REVOKE", target_user_id, actor_user_id, actor_credential_id, reason))
        self.grants.discard(target_user_id)

    def bootstrap_first_operator(self, target_user_id, *, reason):
        self.grants.add(target_user_id)

    def list_events(self):
        return ()


def test_operator_service_requires_individual_durable_identity():
    store = FakeOperatorAccessStore()
    service = OperatorAccessService(store)

    with pytest.raises(OperatorAccessError, match="individually authenticated"):
        service.grant(AuthenticatedIdentity.operator(), uuid4(), "Grant access")


def test_operator_service_requires_operator_permission_and_credential():
    store = FakeOperatorAccessStore()
    service = OperatorAccessService(store)
    user_id = uuid4()

    regular_user = AuthenticatedIdentity.user(user_id)
    with pytest.raises(OperatorAccessError, match="individually authenticated"):
        service.grant(regular_user, uuid4(), "Grant access")

    operator_without_credential = AuthenticatedIdentity.user(
        user_id,
        permissions=frozenset({Permission.OPERATOR}),
    )
    with pytest.raises(OperatorAccessError, match="individually authenticated"):
        service.grant(operator_without_credential, uuid4(), "Grant access")


def test_operator_service_records_actor_and_reason():
    store = FakeOperatorAccessStore()
    service = OperatorAccessService(store)
    actor_id, credential_id, target_id = uuid4(), uuid4(), uuid4()
    actor = AuthenticatedIdentity.user(
        actor_id,
        credential_id=credential_id,
        permissions=frozenset({Permission.OPERATOR}),
    )

    service.grant(actor, target_id, "  Approved operational coverage  ")

    assert store.events == [("GRANT", target_id, actor_id, credential_id, "Approved operational coverage")]


@pytest.mark.parametrize("reason", ["", "   ", "x" * 501])
def test_operator_service_rejects_invalid_reason(reason):
    store = FakeOperatorAccessStore()
    service = OperatorAccessService(store)
    actor = AuthenticatedIdentity.user(
        uuid4(),
        credential_id=uuid4(),
        permissions=frozenset({Permission.OPERATOR}),
    )

    with pytest.raises(OperatorAccessError, match="reason"):
        service.grant(actor, uuid4(), reason)
