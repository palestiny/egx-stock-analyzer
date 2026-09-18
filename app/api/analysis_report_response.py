from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.reporting.report import AnalysisReport


@dataclass(frozen=True)
class AnalysisReportResponse:
    symbol: str
    analysis_date: date
    fundamental_period_end: date
    technical_score: int
    fundamental_score: int
    stock_quality: int
    entry_quality: int
    opportunity: str
    current_price: Decimal | None
    nearest_support: Decimal | None
    nearest_resistance: Decimal | None
    trend: str
    momentum: str
    volume: str
    profitability: str
    liquidity: str
    growth: str

    @classmethod
    def from_report(cls, report: AnalysisReport) -> "AnalysisReportResponse":
        return cls(
            symbol=report.stock_symbol,
            analysis_date=report.analysis_date,
            fundamental_period_end=report.fundamental_analysis.period_end,
            technical_score=report.stock_quality.technical_score.total_score,
            fundamental_score=report.stock_quality.fundamental_score.total,
            stock_quality=report.stock_quality.total_score,
            entry_quality=report.entry_quality.total_score,
            opportunity=report.classification.classification.value,
            current_price=(report.entry_context.current_price.value if report.entry_context.current_price else None),
            nearest_support=(report.entry_context.nearest_support.price.value if report.entry_context.nearest_support else None),
            nearest_resistance=(report.entry_context.nearest_resistance.price.value if report.entry_context.nearest_resistance else None),
            trend=report.technical_analysis.trend.status.value,
            momentum=report.technical_analysis.momentum.status.value,
            volume=report.technical_analysis.volume.status.value,
            profitability=report.fundamental_analysis.profitability.status.value,
            liquidity=report.fundamental_analysis.liquidity.status.value,
            growth=report.fundamental_analysis.growth.status.value,
        )
