from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.application.analysis.stock_analysis import StockAnalysisPipeline
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume


STOCK_ID = UUID("00000000-0000-0000-0000-000000000001")


def _bars() -> list[PriceBar]:
    closes = [10, 12, 11, 14, 13, 16, 15, 18, 17, 20, 19, 22, 21, 24, 23, 26]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        PriceBar.create(
            stock_id=STOCK_ID,
            timeframe=Timeframe.DAILY,
            timestamp=start + timedelta(days=index),
            open=Price(Decimal(str(close - 1))),
            high=Price(Decimal(str(close + 1))),
            low=Price(Decimal(str(close - 1))),
            close=Price(Decimal(str(close))),
            volume=Volume(1000 + index * 100),
        )
        for index, close in enumerate(closes)
    ]


def _periods() -> tuple[FinancialPeriod, FinancialPeriod]:
    return (
        FinancialPeriod(
            period_end=date(2026, 6, 30),
            revenue=Decimal("1200000"),
            net_income=Decimal("180000"),
            current_assets=Decimal("900000"),
            current_liabilities=Decimal("600000"),
        ),
        FinancialPeriod(
            period_end=date(2025, 6, 30),
            revenue=Decimal("1000000"),
            net_income=Decimal("140000"),
            current_assets=Decimal("800000"),
            current_liabilities=Decimal("650000"),
        ),
    )


def test_analysis_computation_workload_is_deterministic():
    current_period, previous_period = _periods()

    first = StockAnalysisPipeline.analyze(
        stock_id=STOCK_ID,
        timeframe=Timeframe.DAILY,
        price_bars=_bars(),
        current_period=current_period,
        previous_period=previous_period,
        momentum_lookback=5,
        volume_lookback=5,
    )
    second = StockAnalysisPipeline.analyze(
        stock_id=STOCK_ID,
        timeframe=Timeframe.DAILY,
        price_bars=_bars(),
        current_period=current_period,
        previous_period=previous_period,
        momentum_lookback=5,
        volume_lookback=5,
    )

    assert first == second
