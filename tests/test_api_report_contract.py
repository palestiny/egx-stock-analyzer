from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.get_analysis_report import GetAnalysisReport
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def make_report_result():
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
            technical_score=SimpleNamespace(total_score=26),
            fundamental_score=SimpleNamespace(total=21),
            total_score=47,
        ),
        entry_context=SimpleNamespace(
            current_price=SimpleNamespace(value=Decimal("350.5")),
            nearest_support=SimpleNamespace(price=SimpleNamespace(value=Decimal("340.0"))),
            nearest_resistance=SimpleNamespace(price=SimpleNamespace(value=Decimal("365.0"))),
        ),
        entry_quality=SimpleNamespace(total_score=2),
        opportunity=SimpleNamespace(
            classification=SimpleNamespace(value="buy"),
        ),
    )


def make_report_capability():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", make_report_result(), analysis_date=date(2026, 9, 16))
    return GetAnalysisReport(InMemoryStockCatalog([stock]), store)


def test_get_report_returns_503_when_reporting_is_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get("/api/v1/reports/EGAL")

    assert response.status_code == 503
    assert response.json() == {"detail": "Analysis reporting is not configured"}


def test_get_report_returns_404_when_report_is_missing():
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_analysis_report=GetAnalysisReport(
            InMemoryStockCatalog([Stock.create("EGAL", "Egypt Aluminum")]),
            InMemoryAnalysisResultStore(),
        ),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/reports/EGAL")

    assert response.status_code == 404
    assert response.json() == {"detail": "Analysis report not found for EGAL"}


def test_get_report_returns_transport_projection_with_analysis_date():
    report_capability = make_report_capability()
    app = create_app(InMemoryAnalysisResultStore(), get_analysis_report=report_capability)

    with TestClient(app) as client:
        response = client.get("/api/v1/reports/EGAL")

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "EGAL",
        "analysis_date": "2026-09-16",
        "fundamental_period_end": "2026-06-30",
        "technical_score": 26,
        "fundamental_score": 21,
        "stock_quality": 47,
        "entry_quality": 2,
        "opportunity": "buy",
        "current_price": "350.5",
        "nearest_support": "340.0",
        "nearest_resistance": "365.0",
        "trend": "uptrend",
        "momentum": "positive",
        "volume": "above_average",
        "profitability": "profitable",
        "liquidity": "above_one",
        "growth": "positive",
    }
