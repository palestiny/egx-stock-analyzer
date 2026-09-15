from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.stocks.stock import Stock
from app.domain.technical_analysis.support_resistance import (
    PriceLevelEvidence,
    SupportResistanceAnalyzer,
    SupportResistanceEvidence,
)


def create_price_bar(
    stock_id,
    timestamp,
    high,
    low,
) -> PriceBar:
    return PriceBar.create(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=timestamp,
        open=Price(Decimal("100")),
        high=Price(Decimal(high)),
        low=Price(Decimal(low)),
        close=Price(Decimal("100")),
        volume=Volume(1_000_000),
    )


# Tests that a strict 3-bar swing low is discovered as a structural support level.
# This exists to verify the core MVP rule: Swing Low → Support Level.
# Its role is to protect support-level detection from regression.
def test_detects_support_from_swing_low():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "105", "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "104", "95"),
        create_price_bar(stock.id, start + timedelta(days=2), "106", "99"),
    ]

    result = SupportResistanceAnalyzer.analyze(
        stock.id,
        Timeframe.DAILY,
        price_bars,
    )

    assert len(result.support_levels) == 1

    level = result.support_levels[0]

    assert level.price == Price(Decimal("95"))
    assert level.timestamp == start + timedelta(days=1)


# Tests that a strict 3-bar swing high is discovered as a structural resistance level.
# This exists to verify the core MVP rule: Swing High → Resistance Level.
# Its role is to protect resistance-level detection from regression.
def test_detects_resistance_from_swing_high():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "105", "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "115", "101"),
        create_price_bar(stock.id, start + timedelta(days=2), "108", "100"),
    ]

    result = SupportResistanceAnalyzer.analyze(
        stock.id,
        Timeframe.DAILY,
        price_bars,
    )

    assert len(result.resistance_levels) == 1

    level = result.resistance_levels[0]

    assert level.price == Price(Decimal("115"))
    assert level.timestamp == start + timedelta(days=1)


# Tests that the analyzer can discover multiple support and resistance levels in one series.
# This exists to verify that all discovered structural swings are preserved as evidence.
# Its role is to protect multi-level detection and ordering from regression.
def test_detects_multiple_structural_levels():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "105", "100"),

        # Swing Low → Support 95
        create_price_bar(
            stock.id,
            start + timedelta(days=1),
            "104",
            "95",
        ),

        # Swing High → Resistance 115
        create_price_bar(
            stock.id,
            start + timedelta(days=2),
            "115",
            "100",
        ),

        # Swing Low → Support 98
        create_price_bar(
            stock.id,
            start + timedelta(days=3),
            "108",
            "98",
        ),

        # Swing High → Resistance 120
        create_price_bar(
            stock.id,
            start + timedelta(days=4),
            "120",
            "102",
        ),

        # Confirms previous swing high
        create_price_bar(
            stock.id,
            start + timedelta(days=5),
            "110",
            "103",
        ),
    ]

    result = SupportResistanceAnalyzer.analyze(
        stock.id,
        Timeframe.DAILY,
        price_bars,
    )

    assert [level.price for level in result.support_levels] == [
        Price(Decimal("95")),
        Price(Decimal("98")),
    ]

    assert [level.price for level in result.resistance_levels] == [
        Price(Decimal("115")),
        Price(Decimal("120")),
    ]


# Tests that the analyzer returns an empty support collection when no swing low exists.
# This exists to verify that absence of support evidence is represented explicitly without inventing a level.
# Its role is to protect the MVP rule that only discovered swings become support levels.
def test_returns_empty_collection_when_no_support_exists():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "100", "95"),
        create_price_bar(
            stock.id,
            start + timedelta(days=1),
            "105",
            "100",
        ),
        create_price_bar(
            stock.id,
            start + timedelta(days=2),
            "110",
            "105",
        ),
    ]

    result = SupportResistanceAnalyzer.analyze(
        stock.id,
        Timeframe.DAILY,
        price_bars,
    )

    assert result.support_levels == ()


# Tests that the analyzer returns an empty resistance collection when no swing high exists.
# This exists to verify that absence of resistance evidence is represented explicitly without inventing a level.
# Its role is to protect the MVP rule that only discovered swings become resistance levels.
def test_returns_empty_collection_when_no_resistance_exists():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "110", "100"),
        create_price_bar(
            stock.id,
            start + timedelta(days=1),
            "105",
            "95",
        ),
        create_price_bar(
            stock.id,
            start + timedelta(days=2),
            "100",
            "90",
        ),
    ]

    result = SupportResistanceAnalyzer.analyze(
        stock.id,
        Timeframe.DAILY,
        price_bars,
    )

    assert result.resistance_levels == ()


# Tests that PriceLevelEvidence cannot be modified after creation.
# This exists because discovered analytical evidence must remain stable once produced.
# Its role is to protect the immutability contract of the evidence value object.
def test_price_level_evidence_is_immutable():
    level = PriceLevelEvidence(
        price=Price(Decimal("365")),
        timestamp=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )

    with pytest.raises(Exception):
        level.price = Price(Decimal("370"))


# Tests that SupportResistanceEvidence cannot be modified after creation.
# This exists because the complete analytical evidence should remain stable once produced.
# Its role is to protect the immutability contract of the result value object.
def test_support_resistance_evidence_is_immutable():
    result = SupportResistanceEvidence(
        support_levels=(),
        resistance_levels=(),
    )

    with pytest.raises(Exception):
        result.support_levels = ()