from app.domain.opportunity.classification import OpportunityClassification
from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.compare_analysis_snapshots import CompareAnalysisSnapshots
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def make_result(score, price):
    return type("Result", (), {
        "technical_score": type("Score", (), {"total_score": score})(),
        "fundamental_score": type("Score", (), {"total": 10})(),
        "stock_quality": type("Score", (), {"total_score": score + 10})(),
        "entry_quality": type("Score", (), {"total_score": 2})(),
        "entry_context": type("Context", (), {
            "current_price": type("Price", (), {"value": Decimal(price)})(),
            "nearest_support": None,
            "nearest_resistance": None,
        })(),
        "opportunity": type("Opportunity", (), {
            "classification": OpportunityClassification.WATCH,
        })(),
    })()


def make_app():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", make_result(20, "350"), date(2026, 9, 16))
    store.save("EGAL", make_result(25, "360"), date(2026, 9, 18))
    history = store.get_history("EGAL")
    capability = CompareAnalysisSnapshots(InMemoryStockCatalog([stock]), store)
    app = create_app(InMemoryAnalysisResultStore(), compare_analysis_snapshots=capability)
    return app, history[1], history[0]


def test_comparison_returns_before_after_and_deltas():
    app, before, after = make_app()
    with TestClient(app) as client:
        response = client.get(f"/api/v1/comparisons/EGAL?before={before.snapshot_id}&after={after.snapshot_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EGAL"
    assert body["before"]["snapshot_id"] == str(before.snapshot_id)
    assert body["after"]["snapshot_id"] == str(after.snapshot_id)
    assert body["deltas"]["technical_score"] == 5
    assert body["deltas"]["current_price"] == 10.0
    assert body["classification_changed"] is False


def test_comparison_rejects_identical_snapshot_ids():
    app, before, _ = make_app()
    with TestClient(app) as client:
        response = client.get(f"/api/v1/comparisons/EGAL?before={before.snapshot_id}&after={before.snapshot_id}")

    assert response.status_code == 400


def test_comparison_returns_404_for_missing_snapshot():
    app, before, _ = make_app()
    with TestClient(app) as client:
        response = client.get(f"/api/v1/comparisons/EGAL?before={before.snapshot_id}&after={uuid4()}")

    assert response.status_code == 404


def test_comparison_returns_400_for_cross_symbol_snapshot():
    egal = Stock.create("EGAL", "Egypt Aluminum")
    other_stock = Stock.create("IEEC", "Ismailia Engineering")
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", make_result(20, "350"), date(2026, 9, 16))
    store.save("IEEC", make_result(10, "5"), date(2026, 9, 18))
    egal_snapshot = store.get_history("EGAL")[0]
    other_snapshot = store.get_history("IEEC")[0]
    capability = CompareAnalysisSnapshots(InMemoryStockCatalog([egal, other_stock]), store)
    app = create_app(InMemoryAnalysisResultStore(), compare_analysis_snapshots=capability)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/comparisons/EGAL?before={egal_snapshot.snapshot_id}&after={other_snapshot.snapshot_id}")

    assert response.status_code == 400
