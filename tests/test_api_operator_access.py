from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.security.operator_access import OperatorAccessService


class FixedAuthenticator:
    def __init__(self, identity):
        self.identity = identity

    def authenticate(self, authorization_header):
        return self.identity


class FakeOperatorAccessStore:
    def __init__(self):
        self.grants = set()
        self.events = []

    def is_operator(self, user_id):
        return user_id in self.grants

    def grant(self, target_user_id, *, actor_user_id, actor_credential_id, reason):
        self.grants.add(target_user_id)
        self.events.append({
            "event_id": len(self.events) + 1,
            "action": "GRANT",
            "target_user_id": target_user_id,
            "actor_user_id": actor_user_id,
            "actor_credential_id": actor_credential_id,
            "actor_kind": "INDIVIDUAL_OPERATOR",
            "reason": reason,
        })

    def revoke(self, target_user_id, *, actor_user_id, actor_credential_id, reason):
        self.grants.discard(target_user_id)
        self.events.append({
            "event_id": len(self.events) + 1,
            "action": "REVOKE",
            "target_user_id": target_user_id,
            "actor_user_id": actor_user_id,
            "actor_credential_id": actor_credential_id,
            "actor_kind": "INDIVIDUAL_OPERATOR",
            "reason": reason,
        })

    def bootstrap_first_operator(self, target_user_id, *, reason):
        self.grants.add(target_user_id)

    def list_events(self):
        from datetime import datetime, timezone
        from app.application.security.operator_access import OperatorAccessEvent
        return tuple(
            OperatorAccessEvent(
                event_id=item["event_id"],
                action=item["action"],
                target_user_id=item["target_user_id"],
                actor_user_id=item["actor_user_id"],
                actor_credential_id=item["actor_credential_id"],
                actor_kind=item["actor_kind"],
                reason=item["reason"],
                occurred_at=datetime.now(timezone.utc),
            )
            for item in self.events
        )


def make_operator_app(identity):
    store = FakeOperatorAccessStore()
    app = create_app(
        InMemoryAnalysisResultStore(),
        authenticator=FixedAuthenticator(identity),
        operator_access_service=OperatorAccessService(store),
    )
    return app, store


def test_individual_operator_can_grant_and_revoke_with_reason():
    actor_id, credential_id, target_id = uuid4(), uuid4(), uuid4()
    identity = AuthenticatedIdentity.user(
        actor_id,
        credential_id=credential_id,
        permissions=frozenset({Permission.OPERATOR}),
    )
    app, store = make_operator_app(identity)

    with TestClient(app) as client:
        granted = client.post(
            f"/api/v1/operators/{target_id}/grant",
            json={"reason": "Approved operational coverage"},
        )
        revoked = client.post(
            f"/api/v1/operators/{target_id}/revoke",
            json={"reason": "Coverage ended"},
        )
        events = client.get("/api/v1/operators/access-events")

    assert granted.status_code == 200
    assert revoked.status_code == 200
    assert events.status_code == 200
    assert [event["action"] for event in events.json()["items"]] == ["GRANT", "REVOKE"]
    assert all(event["actor_user_id"] == str(actor_id) for event in events.json()["items"])
    assert all(event["actor_credential_id"] == str(credential_id) for event in events.json()["items"])
    assert target_id not in store.grants


def test_legacy_shared_operator_cannot_manage_individual_operator_grants():
    app, _ = make_operator_app(AuthenticatedIdentity.operator())

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/operators/{uuid4()}/grant",
            json={"reason": "Must be denied"},
        )

    assert response.status_code == 403


def test_operator_grant_requires_reason():
    actor_id = uuid4()
    identity = AuthenticatedIdentity.user(
        actor_id,
        credential_id=uuid4(),
        permissions=frozenset({Permission.OPERATOR}),
    )
    app, _ = make_operator_app(identity)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/operators/{uuid4()}/grant",
            json={"reason": "   "},
        )

    assert response.status_code == 422
