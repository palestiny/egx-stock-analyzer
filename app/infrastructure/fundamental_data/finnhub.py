from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

import httpx

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.stocks.stock import Stock


class FinnhubFinancialsClient(Protocol):
    def financials(self, symbol: str, statement: str, freq: str) -> dict:
        ...


class HttpxFinnhubFinancialsClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://finnhub.io/api/v1",
        timeout: float = 15.0,
    ) -> None:
        if not api_key:
            raise ValueError("FINNHUB_API_KEY is required")
        self._api_key = api_key
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def financials(self, symbol: str, statement: str, freq: str) -> dict:
        response = self._client.get(
            "/stock/financials",
            params={"symbol": symbol, "statement": statement, "freq": freq, "token": self._api_key},
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()


class FinnhubFundamentalDataProvider:
    """Maps Finnhub annual financial statements into the domain boundary."""

    def __init__(self, client: FinnhubFinancialsClient) -> None:
        self._client = client

    def get_periods(self, stock: Stock, as_of: date) -> tuple[FinancialPeriod, FinancialPeriod]:
        provider_symbol = f"{stock.symbol}.CA"
        income = self._client.financials(provider_symbol, "ic", "annual")
        balance = self._client.financials(provider_symbol, "bs", "annual")
        periods = self._merge_periods(income.get("financials", []), balance.get("financials", []), as_of)
        if len(periods) < 2:
            raise ValueError("Finnhub did not return two usable annual financial periods")
        return periods[0], periods[1]

    @classmethod
    def _merge_periods(cls, income_rows: list[dict], balance_rows: list[dict], as_of: date) -> list[FinancialPeriod]:
        balance_by_period = {
            cls._period_date(row): row for row in balance_rows if cls._period_date(row) is not None
        }
        merged: list[FinancialPeriod] = []
        for income_row in income_rows:
            period_end = cls._period_date(income_row)
            if period_end is None or period_end > as_of:
                continue
            revenue = cls._decimal(income_row.get("totalRevenue", income_row.get("revenue")))
            net_income = cls._decimal(income_row.get("netIncome"))
            if revenue is None or net_income is None:
                continue
            balance_row = balance_by_period.get(period_end, {})
            merged.append(FinancialPeriod(
                period_end=period_end,
                revenue=revenue,
                net_income=net_income,
                current_assets=cls._decimal(balance_row.get("totalCurrentAssets")),
                current_liabilities=cls._decimal(balance_row.get("totalCurrentLiabilities")),
            ))
        return sorted(merged, key=lambda period: period.period_end, reverse=True)

    @staticmethod
    def _period_date(row: dict) -> date | None:
        value = row.get("period") or row.get("date") or row.get("endDate")
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @staticmethod
    def _decimal(value) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))
