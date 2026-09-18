from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.get_alert_candidate import GetAlertCandidate
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock
from app.domain.opportunity.classification import OpportunityClassification


def make_result(classification: str):
    return type("Result", (), {
        "stock_quality": type("Quality", (), {"total_score": 47})(),
        "entry_quality": type("Entry", (), {"total_score": 2})(),
        "opportunity": type("Opportunity", (), {
            "classification": type("Classification", (), {"value": classification})(),
        })(),
    })()


def make_alert_capability(classification: str):
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", make_result(classification), analysis_date=date(2026, 9, 16))
    return GetAlertCandidate(InMemoryStockCatalog([stock]), store), stock


def test_get_alert_returns_503_when_alert_reporting_is_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get("/api/v1/alerts/EGAL")

    assert response.status_code == 503
    assert response.json() == {"detail": "Alert reporting is not configured"}


def test_get_alert_returns_404_when_latest_result_is_not_buy():
    capability, _ = make_alert_capability("watch")
    app = create_app(InMemoryAnalysisResultStore(), get_alert_candidate=capability)

    with TestClient(app) as client:
        response = client.get("/api/v1/alerts/EGAL")

    assert response.status_code == 404
    assert response.json() == {"detail": "Alert candidate not found for EGAL"}


def test_get_alert_returns_buy_candidate_projection():
    capability, stock = make_alert_capability("buy")
    app = create_app(InMemoryAnalysisResultStore(), get_alert_candidate=capability)

    with TestClient(app) as client:
        response = client.get("/api/v1/alerts/EGAL")

    assert response.status_code == 200
    assert response.json() == {
        "stock_id": str(stock.id),
        "classification": "buy",
        "stock_quality_score": 47,
        "entry_quality_score": 2,
    }
