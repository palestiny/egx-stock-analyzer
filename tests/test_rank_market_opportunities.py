from types import SimpleNamespace

import pytest

from app.application.analysis.rank_market_opportunities import (
    MarketOpportunityInput,
    RankMarketOpportunities,
)
from app.domain.opportunity.classification import OpportunityClassification


def analysis_result(
    classification: OpportunityClassification,
    *,
    stock_quality: int,
    entry_quality: int,
    technical: int,
    fundamental: int,
):
    return SimpleNamespace(
        opportunity=SimpleNamespace(classification=classification),
        stock_quality=SimpleNamespace(total_score=stock_quality),
        entry_quality=SimpleNamespace(total_score=entry_quality),
        technical_score=SimpleNamespace(total_score=technical),
        fundamental_score=SimpleNamespace(total=fundamental),
    )


def item(symbol: str, result):
    return MarketOpportunityInput(symbol=symbol, result=result)


def test_empty_input_returns_empty_immutable_set():
    result = RankMarketOpportunities().execute([])

    assert result.items == ()
    assert isinstance(result.items, tuple)


def test_buy_and_watch_are_ranked_while_hold_and_avoid_are_excluded():
    buy = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=6,
        entry_quality=2,
        technical=2,
        fundamental=4,
    )
    watch = analysis_result(
        OpportunityClassification.WATCH,
        stock_quality=3,
        entry_quality=1,
        technical=1,
        fundamental=2,
    )
    hold = analysis_result(
        OpportunityClassification.HOLD,
        stock_quality=9,
        entry_quality=2,
        technical=3,
        fundamental=6,
    )
    avoid = analysis_result(
        OpportunityClassification.AVOID,
        stock_quality=10,
        entry_quality=2,
        technical=3,
        fundamental=7,
    )

    result = RankMarketOpportunities().execute(
        [item("BUY", buy), item("WATCH", watch), item("HOLD", hold), item("AVOID", avoid)]
    )

    assert [entry.symbol for entry in result.items] == ["BUY", "WATCH"]


def test_stock_quality_is_primary_ranking_dimension():
    lower = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=5,
        entry_quality=2,
        technical=3,
        fundamental=2,
    )
    higher = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=7,
        entry_quality=0,
        technical=1,
        fundamental=6,
    )

    result = RankMarketOpportunities().execute(
        [item("LOWER", lower), item("HIGHER", higher)]
    )

    assert [entry.symbol for entry in result.items] == ["HIGHER", "LOWER"]


def test_entry_quality_breaks_stock_quality_tie():
    first = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=6,
        entry_quality=1,
        technical=3,
        fundamental=3,
    )
    second = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=6,
        entry_quality=2,
        technical=1,
        fundamental=5,
    )

    result = RankMarketOpportunities().execute(
        [item("FIRST", first), item("SECOND", second)]
    )

    assert [entry.symbol for entry in result.items] == ["SECOND", "FIRST"]


def test_technical_then_fundamental_then_symbol_break_ties():
    technical_high = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=6,
        entry_quality=1,
        technical=3,
        fundamental=3,
    )
    technical_low = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=6,
        entry_quality=1,
        technical=2,
        fundamental=4,
    )
    same_scores_a = analysis_result(
        OpportunityClassification.WATCH,
        stock_quality=4,
        entry_quality=1,
        technical=2,
        fundamental=2,
    )
    same_scores_b = analysis_result(
        OpportunityClassification.WATCH,
        stock_quality=4,
        entry_quality=1,
        technical=2,
        fundamental=2,
    )

    result = RankMarketOpportunities().execute(
        [
            item("Z-TECH", technical_high),
            item("A-SYMBOL", same_scores_a),
            item("B-SYMBOL", same_scores_b),
            item("A-LOWTECH", technical_low),
        ]
    )

    assert [entry.symbol for entry in result.items] == [
        "Z-TECH",
        "A-LOWTECH",
        "A-SYMBOL",
        "B-SYMBOL",
    ]


def test_fundamental_score_breaks_technical_tie_before_symbol():
    fundamental_high = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=5,
        entry_quality=1,
        technical=2,
        fundamental=4,
    )
    fundamental_low = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=5,
        entry_quality=1,
        technical=2,
        fundamental=3,
    )

    result = RankMarketOpportunities().execute(
        [item("A-LOW", fundamental_low), item("Z-HIGH", fundamental_high)]
    )

    assert [entry.symbol for entry in result.items] == ["Z-HIGH", "A-LOW"]


def test_duplicate_normalized_symbols_are_rejected():
    result = RankMarketOpportunities()
    analysis = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=5,
        entry_quality=1,
        technical=2,
        fundamental=3,
    )

    with pytest.raises(ValueError, match="Duplicate stock symbol"):
        result.execute([item("EGAL", analysis), item(" egal ", analysis)])


def test_original_analysis_result_is_preserved_without_mutation():
    analysis = analysis_result(
        OpportunityClassification.BUY,
        stock_quality=5,
        entry_quality=1,
        technical=2,
        fundamental=3,
    )

    result = RankMarketOpportunities().execute([item("EGAL", analysis)])

    assert result.items[0].result is analysis
