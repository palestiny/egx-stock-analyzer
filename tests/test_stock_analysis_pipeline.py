from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.application.analysis.stock_analysis import StockAnalysisPipeline
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.timeframe import Timeframe


def test_stock_analysis_pipeline_composes_existing_analysis_capabilities():
    stock_id = uuid4()
    price_bars = []
    current_period = FinancialPeriod(
        period_end=date(2026, 9, 15),
        revenue=Decimal("100"),
        net_income=Decimal("10"),
    )
    previous_period = FinancialPeriod(
        period_end=date(2026, 6, 30),
        revenue=Decimal("90"),
        net_income=Decimal("8"),
    )

    technical = object()
    fundamental = object()
    technical_score = object()
    fundamental_score = object()
    stock_quality = object()
    entry_context = object()
    entry_quality = object()
    opportunity = object()

    with (
        patch(
            "app.application.analysis.stock_analysis.TechnicalAnalysisOrchestrator.analyze",
            return_value=technical,
        ) as technical_analyze,
        patch(
            "app.application.analysis.stock_analysis.FundamentalAnalysisOrchestrator.analyze",
            return_value=fundamental,
        ) as fundamental_analyze,
        patch(
            "app.application.analysis.stock_analysis.TechnicalScorer.score",
            return_value=technical_score,
        ) as technical_score_call,
        patch(
            "app.application.analysis.stock_analysis.FundamentalScorer.score",
            return_value=fundamental_score,
        ) as fundamental_score_call,
        patch(
            "app.application.analysis.stock_analysis.StockQualityScorer.score",
            return_value=stock_quality,
        ) as stock_quality_call,
        patch(
            "app.application.analysis.stock_analysis.EntryContextAnalyzer.analyze",
            return_value=entry_context,
        ) as entry_context_call,
        patch(
            "app.application.analysis.stock_analysis.EntryQualityScorer.score",
            return_value=entry_quality,
        ) as entry_quality_call,
        patch(
            "app.application.analysis.stock_analysis.OpportunityClassifier.classify",
            return_value=opportunity,
        ) as opportunity_call,
    ):
        result = StockAnalysisPipeline.analyze(
            stock_id,
            Timeframe.DAILY,
            price_bars,
            current_period,
            previous_period,
            momentum_lookback=5,
            volume_lookback=5,
        )

    technical_analyze.assert_called_once_with(
        stock_id,
        Timeframe.DAILY,
        price_bars,
        5,
        5,
    )
    fundamental_analyze.assert_called_once_with(
        stock_id,
        current_period,
        previous_period,
    )
    technical_score_call.assert_called_once_with(
        technical.trend,
        technical.momentum,
        technical.volume,
    )
    fundamental_score_call.assert_called_once_with(fundamental)
    stock_quality_call.assert_called_once_with(
        fundamental_score,
        technical_score,
    )
    entry_context_call.assert_called_once_with(
        price_bars,
        technical.support_resistance,
    )
    entry_quality_call.assert_called_once_with(entry_context)
    opportunity_call.assert_called_once_with(
        stock_quality,
        entry_quality,
    )

    assert result.technical_analysis is technical
    assert result.fundamental_analysis is fundamental
    assert result.technical_score is technical_score
    assert result.fundamental_score is fundamental_score
    assert result.stock_quality is stock_quality
    assert result.entry_context is entry_context
    assert result.entry_quality is entry_quality
    assert result.opportunity is opportunity
