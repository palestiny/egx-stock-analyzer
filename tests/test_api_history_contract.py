from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def make_result(score: int):
    return SimpleNamespace(
        technical_analysis=SimpleNamespace(
            trend=SimpleNamespace(status=SimpleNamespace(value="uptrend")),
            momentum=SimpleNamespace(status=SimpleNamespace(value="positive")),
            volume=SimpleNamespace(status=SimpleNamespace(value="above_average")),
        ),
        fundamental_analysis=SimpleNamespace(
            period_end=date(2026, 6, 30),
            profitability=SimpleNamespace(status=SimpleNamespace(value="profitable")),
            liquidity=SimpleNamespace(status=SimpleNamespace(value="above_one")),
            growth=SimpleNamespace(status=SimpleNamespace(value="positive")),
        ),
        stock_quality=SimpleNamespace(
            technical_score=SimpleNamespace(total_score=score),
            fundamental_score=SimpleNamespace(total=21),
            total_score=score + 21,
        ),
        entry_context=SimpleNamespace(
            current_price=SimpleNamespace(value=Decimal("350.5")),
            nearest_support=SimpleNamespace(price=SimpleNamespace(value=Decimal("340.0"))),
            nearest_resistance=SimpleNamespace(price=SimpleNamespace(value=Decimal("365.0"))),
        ),
        entry_quality=SimpleNamespace(total_score=2),
        opportunity=SimpleNamespace(classification=SimpleNamespace(value="buy")),
    )


def make_app():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", make_result(26), date(2026, 9, 16))
    store.save("EGAL", make_result(28), date(2026, 9, 18))
    capability = GetAnalysisHistory(InMemoryStockCatalog([stock]), store)
    return create_app(InMemoryAnalysisResultStore(), get_analysis_history=capability)


def test_history_returns_newest_first_with_snapshot_identity():
    app = make_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/history/egal")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EGAL"
    assert [item["report"]["analysis_date"] for item in body["items"]] == ["2026-09-18", "2026-09-16"]
    assert body["items"][0]["snapshot_id"] != body["items"][1]["snapshot_id"]


def test_history_applies_inclusive_date_bounds():
    app = make_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/history/EGAL?from_date=2026-09-16&to_date=2026-09-18")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_history_returns_empty_collection_for_known_symbol_without_history():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    capability = GetAnalysisHistory(InMemoryStockCatalog([stock]), InMemoryAnalysisResultStore())
    app = create_app(InMemoryAnalysisResultStore(), get_analysis_history=capability)
    with TestClient(app) as client:
        response = client.get("/api/v1/history/EGAL")
    assert response.status_code == 200
    assert response.json() == {"symbol": "EGAL", "items": []}


def test_history_returns_404_for_unknown_symbol():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    capability = GetAnalysisHistory(InMemoryStockCatalog([stock]), InMemoryAnalysisResultStore())
    app = create_app(InMemoryAnalysisResultStore(), get_analysis_history=capability)
    with TestClient(app) as client:
        response = client.get("/api/v1/history/UNKNOWN")
    assert response.status_code == 404


def test_history_rejects_reversed_date_range():
    app = make_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/history/EGAL?from_date=2026-09-18&to_date=2026-09-16")
    assert response.status_code == 400
