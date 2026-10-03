from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore


def make_client() -> TestClient:
    return TestClient(create_app(InMemoryAnalysisResultStore()))


def test_public_health_endpoint_is_available() -> None:
    response = make_client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_analysis_read_requires_authentication() -> None:
    response = make_client().get("/api/v1/analysis/COMI")
    assert response.status_code == 401


def test_unconfigured_analysis_execution_returns_503_after_authentication() -> None:
    response = make_client().post(
        "/api/v1/analysis/COMI",
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 503


def test_unconfigured_market_analysis_returns_503_after_authentication() -> None:
    response = make_client().post(
        "/api/v1/market-analysis",
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 503


def test_unconfigured_opportunity_reporting_requires_operator() -> None:
    response = make_client().get(
        "/api/v1/opportunities",
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 403


def test_unconfigured_alert_reporting_requires_operator() -> None:
    response = make_client().get(
        "/api/v1/alerts/COMI",
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 403


def test_unconfigured_comparison_requires_operator() -> None:
    response = make_client().get(
        "/api/v1/comparisons/COMI?before=00000000-0000-0000-0000-000000000001&after=00000000-0000-0000-0000-000000000002",
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 403
