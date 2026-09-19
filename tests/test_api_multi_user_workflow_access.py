from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.execution.get_scheduled_workflow_executions import (
    GetScheduledWorkflowExecutions,
)
from app.application.security.authentication import ConfiguredBearerTokenAuthenticator
from app.domain.identity.user import User, UserStatus
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


def build_app(tmp_path):
    database_path = tmp_path / "workflow.db"
    workflow_store = SQLiteScheduledWorkflowExecutionStore(database_path)
    user_store = SQLiteUserStore(database_path)

    user_a = uuid4()
    user_b = uuid4()
    user_store.save(User(user_a, UserStatus.ACTIVE))
    user_store.save(User(user_b, UserStatus.ACTIVE))

    now = datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc)
    workflow_store.create_or_get("a", now, owner_user_id=user_a)
    workflow_store.create_or_get("b", now, owner_user_id=user_b)

    authenticator = ConfiguredBearerTokenAuthenticator(
        {"token-a": user_a, "token-b": user_b},
        user_store=user_store,
    )
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_scheduled_workflow_executions=GetScheduledWorkflowExecutions(workflow_store),
        authenticator=authenticator,
    )
    return app, user_a, user_b


def test_user_can_list_only_owned_workflows(tmp_path):
    app, _, _ = build_app(tmp_path)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/workflows/executions",
            headers={"Authorization": "Bearer token-a"},
        )

    assert response.status_code == 200
    assert [item["occurrence_id"] for item in response.json()["items"]] == ["a"]


def test_user_cannot_read_another_users_workflow(tmp_path):
    app, _, _ = build_app(tmp_path)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/workflows/executions?occurrence_id=b",
            headers={"Authorization": "Bearer token-a"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_missing_workflow_occurrence_is_404(tmp_path):
    app, _, _ = build_app(tmp_path)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/workflows/executions?occurrence_id=missing",
            headers={"Authorization": "Bearer token-a"},
        )

    assert response.status_code == 404


def test_missing_user_credentials_are_401(tmp_path):
    app, _, _ = build_app(tmp_path)

    with TestClient(app) as client:
        response = client.get("/api/v1/workflows/executions")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_disabled_user_credentials_are_401(tmp_path):
    app, user_a, _ = build_app(tmp_path)
    user_store = SQLiteUserStore(tmp_path / "workflow.db")
    user_store.save(User(user_a, UserStatus.DISABLED))

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/workflows/executions",
            headers={"Authorization": "Bearer token-a"},
        )

    assert response.status_code == 401
