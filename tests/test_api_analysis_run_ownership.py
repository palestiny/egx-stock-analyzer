from datetime import date
from uuid import uuid4
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.get_analysis_run import GetAnalysisRun
from app.application.analysis.list_analysis_runs import ListAnalysisRuns
from app.application.analysis.run_market_analysis import MarketAnalysisResult
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.run_store import InMemoryAnalysisRunStore
from app.application.security.authentication import ConfiguredBearerTokenAuthenticator

from app.domain.analysis_run import AnalysisRun
from app.domain.execution import Execution, ExecutionState
from app.domain.identity.user import User, UserStatus
from app.application.security.identity import LEGACY_OPERATOR_USER_ID


class InMemoryUserStore:
    def __init__(self, users):
        self._users = {user.id: user for user in users}

    def get(self, user_id):
        return self._users.get(user_id)


def make_auth(user_id):
    return ConfiguredBearerTokenAuthenticator(
        {"user-token": user_id},
        user_store=InMemoryUserStore([
            User(user_id, UserStatus.ACTIVE),
            User(LEGACY_OPERATOR_USER_ID, UserStatus.ACTIVE),
        ]),
        legacy_operator_token="operator-token",
    )


def test_user_cannot_get_another_users_analysis_run():
    owner_id = uuid4()
    other_id = uuid4()
    run = AnalysisRun.create(owner_user_id=owner_id)
    run_store = InMemoryAnalysisRunStore()
    run_store.save(run)

    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        get_analysis_run=GetAnalysisRun(run_store, InMemoryAnalysisResultStore()),
        authenticator=make_auth(other_id),
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/analysis-runs/{run.id}",
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 404


def test_user_analysis_run_list_contains_only_owned_runs():
    owner_id = uuid4()
    other_id = uuid4()
    run_store = InMemoryAnalysisRunStore()
    own = AnalysisRun.create(owner_user_id=owner_id)
    other = AnalysisRun.create(owner_user_id=other_id)
    run_store.save(own)
    run_store.save(other)

    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        list_analysis_runs=ListAnalysisRuns(run_store),
        authenticator=make_auth(owner_id),
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis-runs",
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 200
    assert [item["run_id"] for item in response.json()["items"]] == [str(own.id)]


def test_operator_analysis_run_list_includes_user_owned_runs():
    owner_id = uuid4()
    run_store = InMemoryAnalysisRunStore()
    run = AnalysisRun.create(owner_user_id=owner_id)
    run_store.save(run)

    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        list_analysis_runs=ListAnalysisRuns(run_store),
        authenticator=make_auth(owner_id),
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analysis-runs",
            headers={"Authorization": "Bearer operator-token"},
        )

    assert response.status_code == 200
    assert [item["run_id"] for item in response.json()["items"]] == [str(run.id)]


def test_user_market_analysis_receives_authenticated_owner():
    user_id = uuid4()
    execution = Execution.create()
    execution.start()
    execution.complete()
    configured = Mock()
    configured.execute.return_value = MarketAnalysisResult(
        execution=execution,
        analysis_run_id=execution.id,
    )

    app = create_app(
        result_store=InMemoryAnalysisResultStore(),
        run_configured_market_analysis=configured,
        authenticator=make_auth(user_id),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/market-analysis",
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 200
    configured.execute.assert_called_once_with(
        date.today(),
        owner_user_id=user_id,
    )
