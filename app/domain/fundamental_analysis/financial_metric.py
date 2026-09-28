from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class FinancialMetricCode(Enum):
    REVENUE = "revenue"
    NET_OPERATING_INCOME = "net_operating_income"
    NET_INTEREST_INCOME = "net_interest_income"
    NET_PROFIT = "net_profit"


class FinancialMetricScope(Enum):
    CONSOLIDATED = "consolidated"
    STANDALONE = "standalone"


@dataclass(frozen=True)
class FinancialMetric:
    """A financial value whose accounting identity is explicit and traceable."""

    code: FinancialMetricCode
    source_label: str
    scope: FinancialMetricScope
    currency: str
    unit: str
    value: Decimal

    def __post_init__(self) -> None:
        if not self.source_label.strip():
            raise ValueError("source_label cannot be empty")
        if not self.currency.strip():
            raise ValueError("currency cannot be empty")
        if not self.unit.strip():
            raise ValueError("unit cannot be empty")
