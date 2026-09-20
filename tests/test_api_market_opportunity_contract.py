from fastapi.testclient import TestClient
from types import SimpleNamespace

import pytest

from app.api.main import create_app
from app.application.analysis.get_market_opportunity_ranking import GetMarketOpportunityRanking
from app.application.analysis.rank_market_opportunities import RankMarketOpportunities
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.domain.opportunity.classification import OpportunityClassification


def make_result(classification, stock_quality, entry_quality):
    return SimpleNamespace(
        opportunity=SimpleNamespace(classification=classification),
        stock_quality=SimpleNamespace(total_score=stock_quality),
        entry_quality=SimpleNamespace(total_score=entry_quality),
        technical_score=SimpleNamespace(total_score=2),
        fundamental_score=SimpleNamespace(total=1),
    )


def capability():
    store = InMemoryAnalysisResultStore()
    store.save("LOW", make_result(OpportunityClassification.BUY, 4, 1))
    store.save("HIGH", make_result(OpportunityClassification.BUY, 6, 1))
    return GetMarketOpportunityRanking(store, RankMarketOpportunities())


def test_opportunities_returns_503_when_not_configured():
    app = create_app(InMemoryAnalysisResultStore())

    with TestClient(app) as client:
        response = client.get("/api/v1/opportunities?symbols=EGAL")

    assert response.status_code == 503


def test_opportunities_returns_ranked_items_and_missing_symbols():
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_market_opportunity_ranking=capability(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/opportunities?symbols=low,missing,high")

    assert response.status_code == 200
    assert response.json() == {
        "opportunities": [
            {
                "symbol": "HIGH",
                "classification": "buy",
                "stock_quality": 6,
                "entry_quality": 1,
                "technical_score": 2,
                "fundamental_score": 1,
            },
            {
                "symbol": "LOW",
                "classification": "buy",
                "stock_quality": 4,
                "entry_quality": 1,
                "technical_score": 2,
                "fundamental_score": 1,
            },
        ],
        "missing_symbols": ["MISSING"],
    }


def test_opportunities_empty_symbols_returns_empty_view():
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_market_opportunity_ranking=capability(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/opportunities")

    assert response.status_code == 200
    assert response.json() == {"opportunities": [], "missing_symbols": []}


def test_opportunities_duplicate_symbols_return_400():
    app = create_app(
        InMemoryAnalysisResultStore(),
        get_market_opportunity_ranking=capability(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/opportunities?symbols=EGAL,%20egal")

    assert response.status_code == 400
    assert "Duplicate stock symbol" in response.json()["detail"]
