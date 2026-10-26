from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.domain.reporting.session_opportunity_ledger import SessionOpportunityLedgerReport


class FakeLedgerBuilder:
    def execute(self, session_date: date, *, generated_at: datetime) -> SessionOpportunityLedgerReport:
        return SessionOpportunityLedgerReport(
            session_date=session_date,
            generated_at=generated_at,
            exchange_timezone="Africa/Cairo",
            methodology_version="session-opportunity-ledger-v1",
            opportunities=(),
            unresolved_count=0,
            resolved_proxy_count=0,
        )


def test_session_opportunity_ledger_route_returns_session_report() -> None:
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        build_session_opportunity_ledger=FakeLedgerBuilder(),
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/session-opportunity-ledger?session_date=2026-10-26&generated_at=2026-10-26T15:00:00%2B00:00",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_date"] == "2026-10-26"
    assert payload["exchange_timezone"] == "Africa/Cairo"
    assert payload["methodology_version"] == "session-opportunity-ledger-v1"
    assert payload["total_count"] == 0
    assert payload["unresolved_count"] == 0


def test_session_opportunity_ledger_route_rejects_naive_generated_at() -> None:
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        build_session_opportunity_ledger=FakeLedgerBuilder(),
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/session-opportunity-ledger?session_date=2026-10-26&generated_at=2026-10-26T15:00:00",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 422
    assert "timezone" in response.json()["detail"]


def test_session_opportunity_ledger_route_returns_503_when_unconfigured() -> None:
    app = create_app(InMemoryAnalysisResultStore(), operator_token="test-operator-token")
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/session-opportunity-ledger?session_date=2026-10-26",
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 503
