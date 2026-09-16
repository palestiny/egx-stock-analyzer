import pytest

from app.domain.entry_analysis.context import EntryContext
from app.domain.entry_analysis.scoring import EntryQualityScorer
from app.domain.market_data.price import Price
from app.domain.technical_analysis.support_resistance import PriceLevelEvidence
from datetime import datetime, timezone
from decimal import Decimal


def level(price: str) -> PriceLevelEvidence:
    return PriceLevelEvidence(
        price=Price(Decimal(price)),
        timestamp=datetime.now(timezone.utc),
    )


def context(support: str | None, resistance: str | None) -> EntryContext:
    return EntryContext(
        current_price=Price(Decimal("10")),
        nearest_support=level(support) if support else None,
        nearest_resistance=level(resistance) if resistance else None,
    )


def test_support_and_resistance_produce_two_points():
    result = EntryQualityScorer.score(context("9", "11"))

    assert result.total_score == 2


def test_support_only_produces_one_point():
    result = EntryQualityScorer.score(context("9", None))

    assert result.total_score == 1


def test_resistance_only_produces_one_point():
    result = EntryQualityScorer.score(context(None, "11"))

    assert result.total_score == 1


def test_no_levels_produce_zero():
    result = EntryQualityScorer.score(context(None, None))

    assert result.total_score == 0


def test_contributions_are_explainable():
    result = EntryQualityScorer.score(context("9", "11"))

    assert result.support_points == 1
    assert result.resistance_points == 1
    assert result.total_score == 2


def test_result_is_immutable():
    result = EntryQualityScorer.score(context("9", None))

    with pytest.raises(AttributeError):
        result.total_score = 10


def test_scoring_is_deterministic():
    value = context("9", "11")

    first = EntryQualityScorer.score(value)
    second = EntryQualityScorer.score(value)

    assert first == second
