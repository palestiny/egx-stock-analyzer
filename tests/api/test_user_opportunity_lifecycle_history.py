from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore


class EmptyUserOpportunityLifecycleHistory:
    def __init__(self):
        self.user_id = None
        self.limit = None

    def execute(self, user_id, *, limit=50):
        self.user_id = user_id
        self.limit = limit
        return ()


def test_user_lifecycle_history_endpoint_uses_authenticated_identity_only():
    query = EmptyUserOpportunityLifecycleHistory()
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_user_opportunity_lifecycle_history=query,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/me/opportunities?limit=25")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "limit": 25,
        "scope": "telegram_opportunities_addressed_to_authenticated_user",
    }
    assert query.user_id is not None
    assert query.limit == 25


def test_user_lifecycle_history_endpoint_rejects_invalid_limit():
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_user_opportunity_lifecycle_history=EmptyUserOpportunityLifecycleHistory(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/me/opportunities?limit=201")

    assert response.status_code == 400
