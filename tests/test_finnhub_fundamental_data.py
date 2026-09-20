from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.stocks.stock import Stock
from app.infrastructure.fundamental_data.finnhub import (
    FinnhubFundamentalDataProvider,
)


class FakeFinnhubClient:
    def __init__(self, income, balance):
        self.income = income
        self.balance = balance
        self.calls = []

    def financials(self, symbol, statement, freq):
        self.calls.append((symbol, statement, freq))
        if statement == "ic":
            return self.income
        if statement == "bs":
            return self.balance
        raise AssertionError(f"Unexpected statement: {statement}")


def make_stock():
    return Stock.reconstitute(
        id=uuid4(),
        symbol="EGAL",
        name="Egypt Aluminum",
    )


def test_provider_maps_finnhub_annual_statements_to_two_periods():
    client = FakeFinnhubClient(
        income={
            "financials": [
                {
                    "period": "2025-06-30",
                    "totalRevenue": 43_183_100_000,
                    "netIncome": 10_185_590_000,
                },
                {
                    "period": "2024-06-30",
                    "totalRevenue": 32_815_670_000,
                    "netIncome": 9_324_230_000,
                },
            ]
        },
        balance={
            "financials": [
                {
                    "period": "2025-06-30",
                    "totalCurrentAssets": 24_475_360_000,
                    "totalCurrentLiabilities": 6_782_110_000,
                },
                {
                    "period": "2024-06-30",
                    "totalCurrentAssets": 17_040_000_000,
                    "totalCurrentLiabilities": 4_761_000_000,
                },
            ]
        },
    )

    current, previous = FinnhubFundamentalDataProvider(client).get_periods(
        make_stock(),
        date(2026, 9, 16),
    )

    assert current.period_end == date(2025, 6, 30)
    assert current.revenue == Decimal("43183100000")
    assert current.net_income == Decimal("10185590000")
    assert current.current_assets == Decimal("24475360000")
    assert current.current_liabilities == Decimal("6782110000")

    assert previous.period_end == date(2024, 6, 30)
    assert previous.revenue == Decimal("32815670000")
    assert previous.net_income == Decimal("9324230000")

    assert client.calls == [
        ("EGAL.CA", "ic", "annual"),
        ("EGAL.CA", "bs", "annual"),
    ]


def test_provider_ignores_future_periods():
    client = FakeFinnhubClient(
        income={
            "financials": [
                {
                    "period": "2027-06-30",
                    "totalRevenue": 50,
                    "netIncome": 10,
                },
                {
                    "period": "2025-06-30",
                    "totalRevenue": 40,
                    "netIncome": 8,
                },
                {
                    "period": "2024-06-30",
                    "totalRevenue": 30,
                    "netIncome": 6,
                },
            ]
        },
        balance={"financials": []},
    )

    current, previous = FinnhubFundamentalDataProvider(client).get_periods(
        make_stock(),
        date(2026, 9, 16),
    )

    assert current.period_end == date(2025, 6, 30)
    assert previous.period_end == date(2024, 6, 30)
    assert current.current_assets is None
    assert current.current_liabilities is None


def test_provider_requires_two_usable_periods():
    client = FakeFinnhubClient(
        income={
            "financials": [
                {
                    "period": "2025-06-30",
                    "totalRevenue": 40,
                    "netIncome": 8,
                }
            ]
        },
        balance={"financials": []},
    )

    with pytest.raises(ValueError, match="two usable annual financial periods"):
        FinnhubFundamentalDataProvider(client).get_periods(
            make_stock(),
            date(2026, 9, 16),
        )
