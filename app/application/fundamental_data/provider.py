from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.stocks.stock import Stock


@runtime_checkable
class FundamentalDataProvider(Protocol):
    def get_periods(
        self,
        stock: Stock,
        as_of: date,
    ) -> tuple[FinancialPeriod, FinancialPeriod]:
        ...
