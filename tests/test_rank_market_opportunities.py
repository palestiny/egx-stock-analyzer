from types import SimpleNamespace

import pytest

from app.application.analysis.rank_market_opportunities import (
    MarketOpportunityInput,
    RankMarketOpportunities,
)
from app.domain.opportunity.classification import OpportunityClassification


def make_result(classification, stock_quality, entry_quality, technical, fundamental):
    return SimpleNamespace(
        opportunity=SimpleNamespace(classification=classification),
        stock_quality=SimpleNamespace(total_score=stock_quality),
        entry_quality=SimpleNamespace(total_score=entry_quality),
        technical_score=SimpleNamespace(total_score=technical),
        fundamental_score=SimpleNamespace(total=fundamental),
    )


def item(symbol, classification, stock_quality, entry_quality, technical, fundamental):
    return MarketOpportunityInput(
        symbol=symbol,
        result=make_result(classification, stock_quality, entry_quality, technical, fundamental),
    )


def test_empty_input_returns_empty_immutable_set():
    result = RankMarketOpportunities().execute([])

    assert result.opportunities == ()


def test_buy_and_watch_are_ranked_and_hold_avoid_are_excluded():
    result = RankMarketOpportunities().execute([
        item("HOLD", OpportunityClassification.HOLD, 10, 2, 3, 3),
        item("WATCH", OpportunityClassification.WATCH, 3, 1, 1, 1),
        item("AVOID", OpportunityClassification.AVOID, 9, 2, 3, 3),
        item("BUY", OpportunityClassification.BUY, 5, 1, 2, 1),
    ])

    assert [x.symbol for x in result.opportunities] == ["BUY", "WATCH"]


def test_stock_quality_is_primary_ranking_key():
    result = RankMarketOpportunities().execute([
        item("LOW", OpportunityClassification.BUY, 4, 2, 3, 3),
        item("HIGH", OpportunityClassification.BUY, 6, 0, 0, 0),
    ])

    assert [x.symbol for x in result.opportunities] == ["HIGH", "LOW"]


def test_entry_quality_breaks_stock_quality_tie():
    result = RankMarketOpportunities().execute([
        item("LOW_ENTRY", OpportunityClassification.BUY, 5, 1, 3, 2),
        item("HIGH_ENTRY", OpportunityClassification.BUY, 5, 2, 0, 0),
    ])

    assert [x.symbol for x in result.opportunities] == ["HIGH_ENTRY", "LOW_ENTRY"]


def test_technical_then_fundamental_then_symbol_break_remaining_ties():
    result = RankMarketOpportunities().execute([
        item("FUND_HIGH", OpportunityClassification.BUY, 5, 1, 1, 2),
        item("TECH_HIGH", OpportunityClassification.BUY, 5, 1, 2, 1),
        item("A", OpportunityClassification.BUY, 5, 1, 1, 2),
    ])

    assert [x.symbol for x in result.opportunities] == ["TECH_HIGH", "A", "FUND_HIGH"]


def test_symbols_are_normalized_and_duplicates_are_rejected():
    first = item("egal", OpportunityClassification.BUY, 5, 1, 1, 1)
    second = item(" EGAL ", OpportunityClassification.BUY, 4, 1, 1, 1)

    with pytest.raises(ValueError, match="Duplicate stock symbol"):
        RankMarketOpportunities().execute([first, second])


def test_source_result_is_preserved_without_mutation():
    source = make_result(OpportunityClassification.BUY, 5, 2, 1, 2)

    result = RankMarketOpportunities().execute([MarketOpportunityInput("EGAL", source)])

    assert result.opportunities[0].result is source
