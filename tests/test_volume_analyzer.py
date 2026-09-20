from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.stocks.stock import Stock
from app.domain.technical_analysis.volume import (
    VolumeAnalyzer,
    VolumeEvidence,
    VolumeStatus,
)


def create_price_bar(
    stock_id: UUID,
    timestamp: datetime,
    close: str,
    volume: int,
) -> PriceBar:
    return PriceBar.create(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=timestamp,
        open=Price(Decimal(close)),
        high=Price(Decimal(close)),
        low=Price(Decimal(close)),
        close=Price(Decimal(close)),
        volume=Volume(volume),
    )


# Tests that VolumeAnalyzer identifies volume above its previous average.
# This exists because the MVP compares current volume with historical volume rather than using an arbitrary threshold.
# Its function is to prove the ABOVE_AVERAGE outcome.
def test_volume_detects_above_average():
    stock = Stock.create(symbol="COMI", name="Commercial International Bank")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    price_bars = [
        create_price_bar(stock.id, start, "100", 100),
        create_price_bar(stock.id, start + timedelta(days=1), "101", 200),
        create_price_bar(stock.id, start + timedelta(days=2), "102", 200),
    ]

    result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=2)

    assert result.status is VolumeStatus.ABOVE_AVERAGE
    assert result.volume_ratio == Decimal("4") / Decimal("3")


# Tests that VolumeAnalyzer identifies volume below its previous average.
# This exists because lower-than-baseline volume is a distinct descriptive observation.
# Its function is to prove the BELOW_AVERAGE outcome.
def test_volume_detects_below_average():
    stock = Stock.create(symbol="COMI", name="Commercial International Bank")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    price_bars = [
        create_price_bar(stock.id, start, "100", 200),
        create_price_bar(stock.id, start + timedelta(days=1), "101", 200),
        create_price_bar(stock.id, start + timedelta(days=2), "102", 100),
    ]

    result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=2)

    assert result.status is VolumeStatus.BELOW_AVERAGE
    assert result.volume_ratio == Decimal("1") / Decimal("2")


# Tests that VolumeAnalyzer identifies volume equal to its previous average.
# This exists because equality is a valid analytical state without introducing an arbitrary tolerance.
# Its function is to prove the EQUAL_TO_AVERAGE outcome.
def test_volume_detects_equal_to_average():
    stock = Stock.create(symbol="COMI", name="Commercial International Bank")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    price_bars = [
        create_price_bar(stock.id, start, "100", 100),
        create_price_bar(stock.id, start + timedelta(days=1), "101", 200),
        create_price_bar(stock.id, start + timedelta(days=2), "102", 150),
    ]

    result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=2)

    assert result.status is VolumeStatus.EQUAL_TO_AVERAGE
    assert result.volume_ratio == Decimal("1")


# Tests that VolumeAnalyzer preserves the exact calculated volume ratio.
# This exists because evidence should expose the calculation rather than reduce it to a classification.
# Its function is to prove that the ratio remains exact and unrounded.
def test_volume_preserves_exact_ratio():
    stock = Stock.create(symbol="COMI", name="Commercial International Bank")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    price_bars = [
        create_price_bar(stock.id, start, "100", 100),
        create_price_bar(stock.id, start + timedelta(days=1), "101", 100),
        create_price_bar(stock.id, start + timedelta(days=2), "102", 125),
    ]

    result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=2)

    assert result.volume_ratio == Decimal("1.25")


# Tests that VolumeAnalyzer reports insufficient data when fewer than lookback + 1 bars are available.
# This exists because the ratio needs the current volume plus the requested historical baseline.
# Its function is to prevent analysis from being inferred from incomplete history.
def test_volume_returns_insufficient_data_when_history_is_not_enough():
    stock = Stock.create(symbol="COMI", name="Commercial International Bank")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    price_bars = [
        create_price_bar(stock.id, start, "100", 100),
        create_price_bar(stock.id, start + timedelta(days=1), "101", 100),
    ]

    result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=2)

    assert result.status is VolumeStatus.INSUFFICIENT_DATA
    assert result.volume_ratio is None


# Tests that VolumeAnalyzer reports undefined when the historical volume baseline is zero.
# This exists because division by a zero average has no defined numeric result.
# Its function is to protect the dedicated UNDEFINED outcome.
def test_volume_returns_undefined_when_previous_average_is_zero():
    stock = Stock.create(symbol="COMI", name="Commercial International Bank")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    price_bars = [
        create_price_bar(stock.id, start, "100", 0),
        create_price_bar(stock.id, start + timedelta(days=1), "101", 0),
        create_price_bar(stock.id, start + timedelta(days=2), "102", 100),
    ]

    result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=2)

    assert result.status is VolumeStatus.UNDEFINED
    assert result.volume_ratio is None


# Tests that VolumeEvidence is immutable.
# This exists because analytical evidence must not change after it has been calculated.
# Its function is to protect deterministic value semantics.
def test_volume_evidence_is_immutable():
    evidence = VolumeEvidence(
        status=VolumeStatus.ABOVE_AVERAGE,
        volume_ratio=Decimal("1.25"),
    )

    try:
        evidence.status = VolumeStatus.BELOW_AVERAGE
    except AttributeError:
        pass
    else:
        raise AssertionError("VolumeEvidence should be immutable")


# Tests that repeated volume analysis produces the same evidence.
# This exists because the technical-analysis core must be deterministic and reproducible.
# Its function is to protect the analyzer from hidden state or time-dependent behavior.
def test_volume_analysis_is_deterministic():
    stock = Stock.create(symbol="COMI", name="Commercial International Bank")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    price_bars = [
        create_price_bar(stock.id, start, "100", 100),
        create_price_bar(stock.id, start + timedelta(days=1), "101", 100),
        create_price_bar(stock.id, start + timedelta(days=2), "102", 150),
    ]

    first_result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=2)
    second_result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=2)

    assert first_result == second_result


# Tests that VolumeAnalyzer returns the dedicated VolumeEvidence result type.
# This exists because volume is analytical evidence that will later participate in the larger technical-analysis result.
# Its function is to protect the analyzer/result boundary established by the design.
def test_volume_analyzer_returns_volume_evidence():
    stock = Stock.create(symbol="COMI", name="Commercial International Bank")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    price_bars = [
        create_price_bar(stock.id, start, "100", 100),
        create_price_bar(stock.id, start + timedelta(days=1), "101", 100),
    ]

    result = VolumeAnalyzer.analyze(stock.id, Timeframe.DAILY, price_bars, lookback=1)

    assert isinstance(result, VolumeEvidence)
