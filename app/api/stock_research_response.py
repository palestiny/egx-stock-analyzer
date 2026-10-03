from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.application.research.get_stock_research import StockResearchView


@dataclass(frozen=True)
class StockResearchResponse:
    symbol: str
    analysis_date: date
    classification: str
    stock_quality_score: int
    entry_quality_score: int
    current_price: Decimal | None
    nearest_support: Decimal | None
    nearest_resistance: Decimal | None
    trend: str
    momentum: str
    momentum_rate_of_change: Decimal | None
    volume: str
    volume_ratio: Decimal | None
    profitability: Any
    liquidity: Any
    growth: Any

    @classmethod
    def from_view(cls, view: StockResearchView) -> "StockResearchResponse":
        return cls(
            symbol=view.symbol,
            analysis_date=view.analysis_date,
            classification=view.classification.value,
            stock_quality_score=view.stock_quality_score,
            entry_quality_score=view.entry_quality_score,
            current_price=view.current_price,
            nearest_support=view.nearest_support,
            nearest_resistance=view.nearest_resistance,
            trend=view.trend,
            momentum=view.momentum,
            momentum_rate_of_change=view.momentum_rate_of_change,
            volume=view.volume,
            volume_ratio=view.volume_ratio,
            profitability=view.profitability,
            liquidity=view.liquidity,
            growth=view.growth,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
