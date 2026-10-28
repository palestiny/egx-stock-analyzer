from datetime import date, datetime, timezone
from unittest.mock import Mock

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



def test_session_opportunity_report_create_persists_snapshot() -> None:
    report_store = Mock()
    report_store.save.return_value = True
    builder = FakeLedgerBuilder()
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        build_session_opportunity_ledger=builder,
        session_opportunity_report_store=report_store,
    )
    generated_at = "2026-10-26T15:00:00+00:00"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/session-opportunity-reports",
            params={"session_date": "2026-10-26", "generated_at": generated_at},
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 200
    assert response.json()["persisted"] is True
    assert response.json()["created"] is True
    report_store.save.assert_called_once()
    saved_report = report_store.save.call_args.args[0]
    assert saved_report.session_date == date(2026, 10, 26)
    assert saved_report.generated_at == datetime(2026, 10, 26, 15, tzinfo=timezone.utc)


def test_session_opportunity_report_read_returns_404_when_snapshot_missing() -> None:
    report_store = Mock()
    report_store.get_latest.return_value = None
    app = create_app(
        InMemoryAnalysisResultStore(),
        operator_token="test-operator-token",
        session_opportunity_report_store=report_store,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/session-opportunity-reports",
            params={"session_date": "2026-10-26", "as_of": "2026-10-26T16:00:00+00:00"},
            headers={"Authorization": "Bearer test-operator-token"},
        )

    assert response.status_code == 404
    report_store.get_latest.assert_called_once_with(
        date(2026, 10, 26),
        as_of=datetime(2026, 10, 26, 16, tzinfo=timezone.utc),
    )
