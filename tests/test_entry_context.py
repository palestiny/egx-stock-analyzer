from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entry_analysis.context import EntryContextAnalyzer
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.technical_analysis.support_resistance import (
    PriceLevelEvidence,
    SupportResistanceEvidence,
)


def price_bar(close: str) -> PriceBar:
    value = Price(Decimal(close))
    return PriceBar.create(
        stock_id=uuid4(),
        timeframe=Timeframe.DAILY,
        timestamp=datetime.now(timezone.utc),
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Volume(100),
    )


def level(price: str) -> PriceLevelEvidence:
    return PriceLevelEvidence(
        price=Price(Decimal(price)),
        timestamp=datetime.now(timezone.utc),
    )


def test_latest_close_is_current_price():
    bars = [price_bar("9"), price_bar("10")]

    result = EntryContextAnalyzer.analyze(
        bars,
        SupportResistanceEvidence((), ()),
    )

    assert result.current_price == Price(Decimal("10"))


def test_nearest_support_below_current_price_is_selected():
    bars = [price_bar("10")]
    support = (level("7"), level("9"), level("8"))

    result = EntryContextAnalyzer.analyze(
        bars,
        SupportResistanceEvidence(support, ()),
    )

    assert result.nearest_support == level("9")


def test_nearest_resistance_above_current_price_is_selected():
    bars = [price_bar("10")]
    resistance = (level("14"), level("11"), level("12"))

    result = EntryContextAnalyzer.analyze(
        bars,
        SupportResistanceEvidence((), resistance),
    )

    assert result.nearest_resistance == level("11")


def test_levels_on_wrong_side_are_ignored():
    bars = [price_bar("10")]

    result = EntryContextAnalyzer.analyze(
        bars,
        SupportResistanceEvidence(
            support_levels=(level("11"),),
            resistance_levels=(level("9"),),
        ),
    )

    assert result.nearest_support is None
    assert result.nearest_resistance is None


def test_missing_levels_produce_none():
    bars = [price_bar("10")]

    result = EntryContextAnalyzer.analyze(
        bars,
        SupportResistanceEvidence((), ()),
    )

    assert result.nearest_support is None
    assert result.nearest_resistance is None


def test_empty_price_bars_have_no_current_price():
    result = EntryContextAnalyzer.analyze(
        [],
        SupportResistanceEvidence((), ()),
    )

    assert result.current_price is None
    assert result.nearest_support is None
    assert result.nearest_resistance is None


def test_result_is_immutable():
    result = EntryContextAnalyzer.analyze(
        [price_bar("10")],
        SupportResistanceEvidence((), ()),
    )

    with pytest.raises(AttributeError):
        result.current_price = Price(Decimal("11"))


def test_analysis_is_deterministic():
    bars = [price_bar("10")]
    evidence = SupportResistanceEvidence(
        support_levels=(level("9"),),
        resistance_levels=(level("11"),),
    )

    first = EntryContextAnalyzer.analyze(bars, evidence)
    second = EntryContextAnalyzer.analyze(bars, evidence)

    assert first == second
