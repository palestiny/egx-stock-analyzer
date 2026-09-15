from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.stocks.stock import Stock
from app.domain.technical_analysis.momentum import (
    MomentumAnalyzer,
    MomentumEvidence,
    MomentumStatus,
)


def create_price_bar(
    stock_id: UUID,
    timestamp: datetime,
    close: str,
) -> PriceBar:
    return PriceBar.create(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=timestamp,
        open=Price(Decimal(close)),
        high=Price(Decimal(close)),
        low=Price(Decimal(close)),
        close=Price(Decimal(close)),
        volume=Volume(1_000_000),
    )


# Tests that MomentumAnalyzer identifies positive momentum when the current close is above the lookback close.
# This exists because the accepted MVP definition uses the sign of ROC to classify momentum.
# Its function is to prove the POSITIVE outcome.
def test_momentum_detects_positive_roc():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "102"),
        create_price_bar(stock.id, start + timedelta(days=2), "105"),
    ]

    result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=2,
    )

    assert result.status is MomentumStatus.POSITIVE
    assert result.rate_of_change == Decimal("5")


# Tests that MomentumAnalyzer identifies negative momentum when the current close is below the lookback close.
# This exists because ROC must classify downward price movement separately from upward movement.
# Its function is to prove the NEGATIVE outcome.
def test_momentum_detects_negative_roc():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "98"),
        create_price_bar(stock.id, start + timedelta(days=2), "95"),
    ]

    result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=2,
    )

    assert result.status is MomentumStatus.NEGATIVE
    assert result.rate_of_change == Decimal("-5")


# Tests that MomentumAnalyzer identifies neutral momentum when the current close equals the lookback close.
# This exists because ROC can legitimately be exactly zero.
# Its function is to prove the NEUTRAL outcome.
def test_momentum_detects_neutral_roc():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "105"),
        create_price_bar(stock.id, start + timedelta(days=2), "100"),
    ]

    result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=2,
    )

    assert result.status is MomentumStatus.NEUTRAL
    assert result.rate_of_change == Decimal("0")


# Tests that MomentumAnalyzer preserves the exact calculated ROC value.
# This exists because the evidence must expose analytical information rather than only a classification.
# Its function is to prove that the calculation is not rounded or converted into a threshold-based score.
def test_momentum_preserves_exact_roc_value():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "110"),
        create_price_bar(stock.id, start + timedelta(days=2), "115"),
    ]

    result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=2,
    )

    assert result.rate_of_change == Decimal("15")


# Tests that MomentumAnalyzer reports insufficient data when fewer than lookback + 1 observations are available.
# This exists because ROC requires both a current close and a previous close at the requested lookback.
# Its function is to prevent the analyzer from inventing a momentum result from inadequate history.
def test_momentum_returns_insufficient_data_when_history_is_not_enough():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "105"),
    ]

    result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=2,
    )

    assert result.status is MomentumStatus.INSUFFICIENT_DATA


# Tests that ROC becomes undefined when the comparison close is zero.
# This exists because division by zero makes the mathematical ROC undefined, rather than merely insufficient.
# Its function is to protect the dedicated UNDEFINED outcome.
def test_momentum_returns_undefined_when_comparison_close_is_zero():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "0"),
        create_price_bar(stock.id, start + timedelta(days=1), "10"),
    ]

    result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=1,
    )

    assert result.status is MomentumStatus.UNDEFINED


# Tests that MomentumEvidence is immutable.
# This exists because analytical evidence is a value-like result and must not change after calculation.
# Its function is to protect deterministic analysis results.
def test_momentum_evidence_is_immutable():
    evidence = MomentumEvidence(
        status=MomentumStatus.POSITIVE,
        rate_of_change=Decimal("5"),
    )

    try:
        evidence.status = MomentumStatus.NEGATIVE
    except AttributeError:
        pass
    else:
        raise AssertionError("MomentumEvidence should be immutable")


# Tests that repeated momentum analysis produces the same evidence.
# This exists because the core analysis must be deterministic and reproducible.
# Its function is to protect the analyzer from hidden state or time-dependent behavior.
def test_momentum_analysis_is_deterministic():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "102"),
        create_price_bar(stock.id, start + timedelta(days=2), "105"),
    ]

    first_result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=2,
    )

    second_result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=2,
    )

    assert first_result == second_result


# Tests that MomentumAnalyzer returns the dedicated MomentumEvidence result type.
# This exists because momentum is analytical evidence that will later participate in the larger technical-analysis result.
# Its function is to protect the analyzer/result boundary established by the design.
def test_momentum_analyzer_returns_momentum_evidence():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(stock.id, start, "100"),
        create_price_bar(stock.id, start + timedelta(days=1), "102"),
    ]

    result = MomentumAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
        lookback=1,
    )

    assert isinstance(result, MomentumEvidence)