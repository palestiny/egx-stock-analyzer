from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class FinancialPeriod:
    period_end: date
    revenue: Decimal
    net_income: Decimal
