from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.entry_analysis.context import EntryContext
from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
from app.domain.opportunity.classification import OpportunityClassificationResult
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.technical_analysis.result import TechnicalAnalysisResult


@dataclass(frozen=True)
class AnalysisReport:
    stock_id: UUID
    stock_symbol: str
    analysis_date: date
    technical_analysis: TechnicalAnalysisResult
    fundamental_analysis: FundamentalAnalysisResult
    stock_quality: StockQualityScore
    entry_context: EntryContext
    entry_quality: EntryQualityScore
    classification: OpportunityClassificationResult

    @classmethod
    def create(
        cls,
        stock_id: UUID,
        stock_symbol: str,
        analysis_date: date,
        technical_analysis: TechnicalAnalysisResult,
        fundamental_analysis: FundamentalAnalysisResult,
        stock_quality: StockQualityScore,
        entry_context: EntryContext,
        entry_quality: EntryQualityScore,
        classification: OpportunityClassificationResult,
    ) -> "AnalysisReport":
        return cls(
            stock_id=stock_id,
            stock_symbol=stock_symbol,
            analysis_date=analysis_date,
            technical_analysis=technical_analysis,
            fundamental_analysis=fundamental_analysis,
            stock_quality=stock_quality,
            entry_context=entry_context,
            entry_quality=entry_quality,
            classification=classification,
        )
