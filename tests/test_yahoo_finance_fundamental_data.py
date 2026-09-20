from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.stocks.stock import Stock
from app.infrastructure.market_data.yahoo_finance import (
    YahooFinanceFundamentalDataSource,
)


class FakeSeries:
    def __init__(self, values):
        self._values = values

    def items(self):
        return self._values.items()


class FakeDataFrame:
    def __init__(self, columns, rows_by_metric):
        self.columns = columns
        self._rows_by_metric = rows_by_metric
        self.empty = not columns

    def __getitem__(self, column):
        return FakeSeries(
            {
                metric: values[column]
                for metric, values in self._rows_by_metric.items()
            }
        )


class FakeTicker:
    def __init__(self, income_stmt, balance_sheet):
        self.income_stmt = income_stmt
        self.balance_sheet = balance_sheet


class FakeYFinance:
    def __init__(self, ticker):
        self._ticker = ticker

    def Ticker(self, symbol):
        assert symbol == "EGAL.CA"
        return self._ticker


def make_stock():
    return Stock.reconstitute(
        id=uuid4(),
        symbol="EGAL",
        name="Egypt Aluminum",
    )


def test_yahoo_fundamental_source_maps_two_annual_periods():
    columns = [date(2025, 6, 30), date(2024, 6, 30)]
    income = FakeDataFrame(
        columns,
        {
            "Total Revenue": {
                columns[0]: 43_183_100_000,
                columns[1]: 32_815_670_000,
            },
            "Net Income": {
                columns[0]: 10_185_590_052,
                columns[1]: 9_324_234_387,
            },
        },
    )
    balance = FakeDataFrame(
        columns,
        {
            "Current Assets": {
                columns[0]: 24_475_360_000,
                columns[1]: 17_040_000_000,
            },
            "Current Liabilities": {
                columns[0]: 6_782_110_000,
                columns[1]: 4_761_000_000,
            },
        },
    )

    source = YahooFinanceFundamentalDataSource(
        FakeYFinance(FakeTicker(income, balance))
    )

    current, previous = source.get_periods(
        make_stock(),
        date(2026, 9, 16),
    )

    assert current.period_end == date(2025, 6, 30)
    assert current.revenue == Decimal("43183100000")
    assert current.net_income == Decimal("10185590052")
    assert current.current_assets == Decimal("24475360000")
    assert current.current_liabilities == Decimal("6782110000")

    assert previous.period_end == date(2024, 6, 30)
    assert previous.revenue == Decimal("32815670000")
    assert previous.net_income == Decimal("9324234387")


def test_yahoo_fundamental_source_ignores_future_periods():
    columns = [date(2027, 6, 30), date(2025, 6, 30), date(2024, 6, 30)]
    income = FakeDataFrame(
        columns,
        {
            "Total Revenue": {column: index + 1 for index, column in enumerate(columns)},
            "Net Income": {column: index + 10 for index, column in enumerate(columns)},
        },
    )
    balance = FakeDataFrame([], {})

    source = YahooFinanceFundamentalDataSource(
        FakeYFinance(FakeTicker(income, balance))
    )

    current, previous = source.get_periods(
        make_stock(),
        date(2026, 9, 16),
    )

    assert current.period_end == date(2025, 6, 30)
    assert previous.period_end == date(2024, 6, 30)


def test_yahoo_fundamental_source_requires_two_periods():
    columns = [date(2025, 6, 30)]
    income = FakeDataFrame(
        columns,
        {
            "Total Revenue": {columns[0]: 40},
            "Net Income": {columns[0]: 8},
        },
    )

    source = YahooFinanceFundamentalDataSource(
        FakeYFinance(FakeTicker(income, FakeDataFrame([], {})))
    )

    with pytest.raises(ValueError, match="two usable annual financial periods"):
        source.get_periods(make_stock(), date(2026, 9, 16))
