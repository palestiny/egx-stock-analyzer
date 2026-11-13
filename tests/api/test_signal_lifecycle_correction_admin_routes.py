from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.security.authentication import AuthenticationError
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.signals.lifecycle_unit_of_work import LifecycleCorrectionReviewDecision


OPERATOR_TOKEN = "lifecycle-review-operator-token"
OPERATOR_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SIGNAL_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CORRECTION_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class LifecycleReviewAuthenticator:
    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        if authorization_header == f"Bearer {OPERATOR_TOKEN}":
            return AuthenticatedIdentity.user(
                OPERATOR_ID,
                credential_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
                permissions=frozenset({Permission.OPERATOR}),
            )
        raise AuthenticationError("Invalid credentials")


class FakeLifecycleOrchestrator:
    def __init__(self) -> None:
        self.review: LifecycleCorrectionReviewDecision | None = None

    def lifecycle_corrections(self, signal_id):
        assert signal_id == SIGNAL_ID
        return ()

    def lifecycle_correction_review_decisions(self, signal_id):
        assert signal_id == SIGNAL_ID
        return ()

    def record_daily_bar_correction_review(
        self, signal_id, correction_id, *, decision, reviewer_id, reason, recorded_at
    ):
        assert signal_id == SIGNAL_ID
        assert correction_id == CORRECTION_ID
        self.review = LifecycleCorrectionReviewDecision(
            decision_id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            correction_id=correction_id,
            signal_id=signal_id,
            decision=decision,
            reviewer_id=reviewer_id,
            reason=reason,
            recorded_at=recorded_at,
        )
        return self.review


def make_client(orchestrator=None):
    return TestClient(
        create_app(
            result_store=InMemoryAnalysisResultStore(),
            authenticator=LifecycleReviewAuthenticator(),
            signal_lifecycle_orchestrator=orchestrator,
        )
    )


def operator_headers():
    return {"Authorization": f"Bearer {OPERATOR_TOKEN}"}


def test_lifecycle_correction_review_requires_authenticated_operator():
    client = make_client(FakeLifecycleOrchestrator())

    response = client.post(
        f"/api/v1/owner/signals/{SIGNAL_ID}/lifecycle-corrections/{CORRECTION_ID}/review",
        json={
            "decision": "ACCEPTED_NO_STATE_CHANGE",
            "reason": "Independent review completed",
        },
    )

    assert response.status_code == 401


def test_lifecycle_correction_review_is_operator_attributed_and_append_only():
    orchestrator = FakeLifecycleOrchestrator()
    client = make_client(orchestrator)

    response = client.post(
        f"/api/v1/owner/signals/{SIGNAL_ID}/lifecycle-corrections/{CORRECTION_ID}/review",
        headers=operator_headers(),
        json={
            "decision": "ACCEPTED_NO_STATE_CHANGE",
            "reason": "Independent review completed",
            "recorded_at": "2026-11-13T09:30:00+00:00",
        },
    )

    assert response.status_code == 201
    assert response.json()["reviewer_id"] == str(OPERATOR_ID)
    assert response.json()["decision"] == "ACCEPTED_NO_STATE_CHANGE"
    assert orchestrator.review is not None
    assert orchestrator.review.reason == "Independent review completed"


def test_lifecycle_correction_review_rejects_naive_timestamp():
    client = make_client(FakeLifecycleOrchestrator())

    response = client.post(
        f"/api/v1/owner/signals/{SIGNAL_ID}/lifecycle-corrections/{CORRECTION_ID}/review",
        headers=operator_headers(),
        json={
            "decision": "REPLAY_REQUIRED",
            "reason": "Potential state impact",
            "recorded_at": "2026-11-13T09:30:00",
        },
    )

    assert response.status_code == 422


def test_lifecycle_correction_review_returns_service_unavailable_when_unconfigured():
    client = make_client()

    response = client.get(
        f"/api/v1/owner/signals/{SIGNAL_ID}/lifecycle-corrections",
        headers=operator_headers(),
    )

    assert response.status_code == 503
