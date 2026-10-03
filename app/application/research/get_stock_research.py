from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.reporting.get_analysis_report import GetAnalysisReport
from app.application.security.identity import AuthenticatedIdentity
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.reporting.report import AnalysisReport


@dataclass(frozen=True)
class StockResearchView:
    symbol: str
    analysis_date: date
    classification: OpportunityClassification
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
    profitability: object
    liquidity: object
    growth: object


class StockResearchNotFoundError(ValueError):
    pass


class GetStockResearch:
    def __init__(self, get_analysis_report: GetAnalysisReport) -> None:
        self._get_analysis_report = get_analysis_report

    def execute(
        self,
        symbol: str,
        identity: AuthenticatedIdentity | None = None,
    ) -> StockResearchView:
        report = self._get_analysis_report.execute(symbol, identity=identity)
        if report is None:
            raise StockResearchNotFoundError(
                f"Stock research not found for {symbol.strip().upper()}"
            )
        return self._to_view(report)

    @staticmethod
    def _to_view(report: AnalysisReport) -> StockResearchView:
        technical = report.technical_analysis
        entry = report.entry_context

        return StockResearchView(
            symbol=report.stock_symbol,
            analysis_date=report.analysis_date,
            classification=report.classification.classification,
            stock_quality_score=report.stock_quality.total_score,
            entry_quality_score=report.entry_quality.total_score,
            current_price=entry.current_price.value if entry.current_price else None,
            nearest_support=entry.nearest_support.price.value if entry.nearest_support else None,
            nearest_resistance=(
                entry.nearest_resistance.price.value
                if entry.nearest_resistance
                else None
            ),
            trend=technical.trend.status.value,
            momentum=technical.momentum.status.value,
            momentum_rate_of_change=technical.momentum.rate_of_change,
            volume=technical.volume.status.value,
            volume_ratio=technical.volume.volume_ratio,
            profitability=report.fundamental_analysis.profitability,
            liquidity=report.fundamental_analysis.liquidity,
            growth=report.fundamental_analysis.growth,
        )
