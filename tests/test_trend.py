from datetime import datetime, timedelta, timezone
from decimal import Decimal
from tracemalloc import start
from uuid import UUID

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume

from app.domain.stocks.stock import Stock
from app.domain.technical_analysis.trend import TrendAnalyzer , TrendEvidence, TrendStatus


def create_price_bar(
    stock_id: UUID,
    timestamp: datetime,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> PriceBar:
    return PriceBar.create(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=timestamp,
        open=Price(Decimal(open_price)),
        high=Price(Decimal(high)),
        low=Price(Decimal(low)),
        close=Price(Decimal(close)),
        volume=Volume(1_000_000),
    )


# Tests that TrendAnalyzer detects an uptrend from higher highs and higher lows.
# This exists because the accepted trend definition is based on price structure rather than simply comparing first and last prices.
# Its function is to prove that two confirmed swing highs and swing lows form the expected upward structure.
def test_trend_analyzer_detects_uptrend_from_higher_highs_and_higher_lows():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime.now(timezone.utc)

    price_bars = [
    # Bar 1
    create_price_bar(
        stock.id,
        start,
        "100",
        "102",
        "98",
        "101",
    ),

    # Bar 2 — First Swing Low
    create_price_bar(
        stock.id,
        start + timedelta(days=1),
        "101",
        "104",
        "95",
        "97",
    ),

    # Bar 3 — First Swing High
    create_price_bar(
        stock.id,
        start + timedelta(days=2),
        "97",
        "110",
        "105",
        "108",
    ),

    # Bar 4 — Second Swing Low / Higher Low
    create_price_bar(
        stock.id,
        start + timedelta(days=3),
        "108",
        "109",
        "100",
        "102",
    ),

    # Bar 5 — Second Swing High / Higher High
    create_price_bar(
        stock.id,
        start + timedelta(days=4),
        "102",
        "115",
        "101",
        "113",
    ),

    # Bar 6 — Confirms Bar 5 is a Swing High
    create_price_bar(
        stock.id,
        start + timedelta(days=5),
        "113",
        "112",
        "105",
        "108",
    ),
]

    result = TrendAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
    )

    assert result.status is TrendStatus.UPTREND


# Tests that TrendAnalyzer detects a downtrend from lower highs and lower lows.
# This exists because the trend definition must work symmetrically in the downward direction.
# Its function is to prove that confirmed swing structure produces DOWNTREND when both highs and lows decline.
def test_trend_analyzer_detects_downtrend_from_lower_highs_and_lower_lows():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
    # Bar 1
    create_price_bar(
        stock.id,
        start,
        "113",
        "115",
        "110",
        "112",
    ),

    # Bar 2 — First Swing High
    create_price_bar(
        stock.id,
        start + timedelta(days=1),
        "112",
        "120",
        "108",
        "110",
    ),

    # Bar 3 — First Swing Low
    create_price_bar(
        stock.id,
        start + timedelta(days=2),
        "110",
        "110",
        "100",
        "103",
    ),

    # Bar 4 — Second Swing High / Lower High
    create_price_bar(
        stock.id,
        start + timedelta(days=3),
        "103",
        "112",
        "101",
        "105",
    ),

    # Bar 5 — Second Swing Low / Lower Low
    create_price_bar(
        stock.id,
        start + timedelta(days=4),
        "105",
        "105",
        "95",
        "98",
    ),

    # Bar 6 — Confirms Bar 5 is a Swing Low
    create_price_bar(
        stock.id,
        start + timedelta(days=5),
        "98",
        "104",
        "96",
        "100",
    ),
]

    result = TrendAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
    )

    assert result.status is TrendStatus.DOWNTREND


# Tests that enough swing structure without a consistent direction produces SIDEWAYS.
# This exists because not every market structure is an uptrend or downtrend.
# Its function is to distinguish mixed/non-directional structure from a directional trend.
def test_trend_analyzer_returns_sideways_when_no_clear_direction_exists():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
    # Bar 1
    create_price_bar(
        stock.id,
        start,
        "100",
        "102",
        "98",
        "101",
    ),

    # Bar 2 — First Swing High
    create_price_bar(
        stock.id,
        start + timedelta(days=1),
        "101",
        "110",
        "95",
        "105",
    ),

    # Bar 3 — First Swing Low
    create_price_bar(
        stock.id,
        start + timedelta(days=2),
        "105",
        "106",
        "90",
        "93",
    ),

    # Bar 4 — Second Swing High / Lower High
    create_price_bar(
        stock.id,
        start + timedelta(days=3),
        "93",
        "108",
        "96",
        "105",
    ),

    # Bar 5 — Second Swing Low / Higher Low
    create_price_bar(
        stock.id,
        start + timedelta(days=4),
        "105",
        "107",
        "94",
        "96",
    ),

    # Bar 6 — Confirms Bar 5 is a Swing Low
    create_price_bar(
        stock.id,
        start + timedelta(days=5),
        "96",
        "103",
        "95",
        "100",
    ),
]

    result = TrendAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
    )

    assert result.status is TrendStatus.SIDEWAYS


# Tests that TrendAnalyzer reports insufficient data when there are not enough observations to establish the required structure.
# This exists because the analyzer must not guess a trend from inadequate history.
# Its function is to protect the INSUFFICIENT_DATA outcome for incomplete input.
def test_trend_analyzer_returns_insufficient_data_when_history_is_not_enough():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    price_bars = [
        create_price_bar(
            stock.id,
            datetime(2026, 9, 1, tzinfo=timezone.utc),
            "100",
            "105",
            "98",
            "103",
        )
    ]

    result = TrendAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
    )

    assert result.status is TrendStatus.INSUFFICIENT_DATA


# Tests that running the same trend analysis twice over the same observations produces the same result.
# This exists because the core analysis must be deterministic and reproducible.
# Its function is to protect the analyzer from hidden state or time-dependent variation.
def test_trend_analysis_is_deterministic():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime(2026, 9, 1, tzinfo=timezone.utc)

    price_bars = [
        create_price_bar(
            stock.id,
            start,
            "100",
            "102",
            "98",
            "101",
        ),

        create_price_bar(
            stock.id,
            start + timedelta(days=1),
            "101",
            "104",
            "95",
            "97",
        ),

        create_price_bar(
            stock.id,
            start + timedelta(days=2),
            "97",
            "110",
            "105",
            "108",
        ),

        create_price_bar(
            stock.id,
            start + timedelta(days=3),
            "108",
            "109",
            "100",
            "102",
        ),

        create_price_bar(
            stock.id,
            start + timedelta(days=4),
            "102",
            "115",
            "101",
            "113",
        ),
    ]

    first_result = TrendAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
    )

    second_result = TrendAnalyzer.analyze(
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=price_bars,
    )

    assert first_result == second_result


# Tests that TrendAnalyzer returns the dedicated TrendEvidence result type rather than a raw enum value.
# This exists because the architecture treats trend as analytical evidence that will later be combined with other evidence.
# Its function is to protect the analyzer/result boundary established in the technical-analysis design.
def test_trend_analyzer_returns_trend_evidence():
    stock = Stock.create(
        symbol="COMI",
        name="Commercial International Bank",
    )

    start = datetime.now(timezone.utc)

    price_bars = [
            create_price_bar(
                stock.id,
                start,
                "100",
                "102",
                "98",
                "101",
            ),
    
            create_price_bar(
                stock.id,
                start + timedelta(days=1),
                "101",
                "104",
                "95",
                "97",
            ),
    
            create_price_bar(
                stock.id,
                start + timedelta(days=2),
                "97",
                "110",
                "105",
                "108",
            ),
    
            create_price_bar(
                stock.id,
                start + timedelta(days=3),
                "108",
                "109",
                "100",
                "102",
            ),
    
            create_price_bar(
                stock.id,
                start + timedelta(days=4),
                "102",
                "115",
                "101",
                "113",
            ), 
            create_price_bar(
                stock.id,
                start + timedelta(days=5),
                "111",
                "112",
                "105",
                "108",
            ),
        ]

    result = TrendAnalyzer.analyze(
        stock.id,
        Timeframe.DAILY,
        price_bars,
    )

    assert isinstance(result, TrendEvidence)
    assert result.status is TrendStatus.UPTREND