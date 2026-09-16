from dataclasses import dataclass
from uuid import UUID

from app.domain.entry_analysis.context import EntryContext
from app.domain.entry_analysis.scoring import EntryQualityScore, EntryQualityScorer
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.orchestrator import FundamentalAnalysisOrchestrator
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
from app.domain.fundamental_analysis.scoring import FundamentalScore, FundamentalScorer
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.opportunity.classification import (
    OpportunityClassificationResult,
    OpportunityClassifier,
)
from app.domain.scoring.stock_quality import StockQualityScore, StockQualityScorer
from app.domain.technical_analysis.orchestrator import TechnicalAnalysisOrchestrator
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.scoring import TechnicalScore, TechnicalScorer


@dataclass(frozen=True)
class StockAnalysisResult:
    technical_analysis: TechnicalAnalysisResult
    fundamental_analysis: FundamentalAnalysisResult
    technical_score: TechnicalScore
    fundamental_score: FundamentalScore
    stock_quality: StockQualityScore
    entry_context: EntryContext
    entry_quality: EntryQualityScore
    opportunity: OpportunityClassificationResult


class StockAnalysisPipeline:
    @staticmethod
    def analyze(
        stock_id: UUID,
        timeframe: Timeframe,
        price_bars: list[PriceBar],
        current_period: FinancialPeriod,
        previous_period: FinancialPeriod,
        momentum_lookback: int,
        volume_lookback: int,
    ) -> StockAnalysisResult:
        technical_analysis = TechnicalAnalysisOrchestrator.analyze(
            stock_id,
            timeframe,
            price_bars,
            momentum_lookback,
            volume_lookback,
        )
        fundamental_analysis = FundamentalAnalysisOrchestrator.analyze(
            stock_id,
            current_period,
            previous_period,
        )

        technical_score = TechnicalScorer.score(
            technical_analysis.trend,
            technical_analysis.momentum,
            technical_analysis.volume,
        )
        fundamental_score = FundamentalScorer.score(fundamental_analysis)
        stock_quality = StockQualityScorer.score(
            fundamental_score,
            technical_score,
        )

        entry_context = __import__(
            "app.domain.entry_analysis.context",
            fromlist=["EntryContextAnalyzer"],
        ).EntryContextAnalyzer.analyze(
            price_bars,
            technical_analysis.support_resistance,
        )
        entry_quality = EntryQualityScorer.score(entry_context)
        opportunity = OpportunityClassifier.classify(
            stock_quality,
            entry_quality,
        )

        return StockAnalysisResult(
            technical_analysis=technical_analysis,
            fundamental_analysis=fundamental_analysis,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            stock_quality=stock_quality,
            entry_context=entry_context,
            entry_quality=entry_quality,
            opportunity=opportunity,
        )
