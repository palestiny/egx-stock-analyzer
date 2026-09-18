from types import SimpleNamespace

import pytest

from app.application.analysis.get_market_opportunity_ranking import (
    GetMarketOpportunityRanking,
)
from app.application.analysis.rank_market_opportunities import RankMarketOpportunities
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.domain.opportunity.classification import OpportunityClassification


def result(classification: OpportunityClassification, stock_quality: int, entry_quality: int):
    return SimpleNamespace(
        opportunity=SimpleNamespace(classification=classification),
        stock_quality=SimpleNamespace(total_score=stock_quality),
        entry_quality=SimpleNamespace(total_score=entry_quality),
        technical_score=SimpleNamespace(total_score=1),
        fundamental_score=SimpleNamespace(total=1),
    )


def test_empty_symbols_return_empty_view():
    view = GetMarketOpportunityRanking(
        InMemoryAnalysisResultStore(),
        RankMarketOpportunities(),
    ).execute([])

    assert view.opportunities == ()
    assert view.missing_symbols == ()


def test_reads_stored_results_and_preserves_ranking_order():
    store = InMemoryAnalysisResultStore()
    store.save("LOW", result(OpportunityClassification.BUY, 4, 1))
    store.save("HIGH", result(OpportunityClassification.BUY, 6, 1))

    view = GetMarketOpportunityRanking(store, RankMarketOpportunities()).execute(
        ["low", "high"]
    )

    assert [item.symbol for item in view.opportunities] == ["HIGH", "LOW"]


def test_missing_results_are_reported_and_excluded():
    store = InMemoryAnalysisResultStore()
    store.save("EGAL", result(OpportunityClassification.BUY, 5, 1))

    view = GetMarketOpportunityRanking(store, RankMarketOpportunities()).execute(
        ["EGAL", "IEEC"]
    )

    assert [item.symbol for item in view.opportunities] == ["EGAL"]
    assert view.missing_symbols == ("IEEC",)


def test_duplicate_normalized_symbols_are_rejected():
    capability = GetMarketOpportunityRanking(
        InMemoryAnalysisResultStore(),
        RankMarketOpportunities(),
    )

    with pytest.raises(ValueError, match="Duplicate stock symbol"):
        capability.execute(["EGAL", " egal "])


def test_missing_results_are_not_converted_to_synthetic_scores():
    store = InMemoryAnalysisResultStore()

    view = GetMarketOpportunityRanking(store, RankMarketOpportunities()).execute(
        ["UNKNOWN"]
    )

    assert view.opportunities == ()
    assert view.missing_symbols == ("UNKNOWN",)
