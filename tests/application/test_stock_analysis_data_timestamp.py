from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.application.analysis.stock_analysis import StockAnalysisPipeline
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume


def make_bar(stock_id, timestamp):
    price = Price(Decimal("10"))
    return PriceBar(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        timestamp=timestamp,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Volume(100),
    )


def test_analysis_result_preserves_latest_source_bar_timestamp():
    stock_id = uuid4()
    earlier = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
    latest = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
    bars = [make_bar(stock_id, latest), make_bar(stock_id, earlier)]

    with (
        patch("app.application.analysis.stock_analysis.TechnicalAnalysisOrchestrator.analyze", return_value=object()),
        patch("app.application.analysis.stock_analysis.FundamentalAnalysisOrchestrator.analyze", return_value=object()),
        patch("app.application.analysis.stock_analysis.TechnicalScorer.score", return_value=object()),
        patch("app.application.analysis.stock_analysis.FundamentalScorer.score", return_value=object()),
        patch("app.application.analysis.stock_analysis.StockQualityScorer.score", return_value=object()),
        patch("app.application.analysis.stock_analysis.EntryContextAnalyzer.analyze", return_value=object()),
        patch("app.application.analysis.stock_analysis.EntryQualityScorer.score", return_value=object()),
        patch("app.application.analysis.stock_analysis.OpportunityClassifier.classify", return_value=object()),
    ):
        result = StockAnalysisPipeline.analyze(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            price_bars=bars,
            current_period=FinancialPeriod(date(2026, 9, 30), Decimal("100"), Decimal("10")),
            previous_period=FinancialPeriod(date(2026, 6, 30), Decimal("90"), Decimal("8")),
            momentum_lookback=5,
            volume_lookback=5,
        )

    assert result.data_timestamp == latest


def test_analysis_result_has_no_source_timestamp_when_no_bars_exist():
    with (
        patch("app.application.analysis.stock_analysis.TechnicalAnalysisOrchestrator.analyze", return_value=object()),
        patch("app.application.analysis.stock_analysis.FundamentalAnalysisOrchestrator.analyze", return_value=object()),
        patch("app.application.analysis.stock_analysis.TechnicalScorer.score", return_value=object()),
        patch("app.application.analysis.stock_analysis.FundamentalScorer.score", return_value=object()),
        patch("app.application.analysis.stock_analysis.StockQualityScorer.score", return_value=object()),
        patch("app.application.analysis.stock_analysis.EntryContextAnalyzer.analyze", return_value=object()),
        patch("app.application.analysis.stock_analysis.EntryQualityScorer.score", return_value=object()),
        patch("app.application.analysis.stock_analysis.OpportunityClassifier.classify", return_value=object()),
    ):
        result = StockAnalysisPipeline.analyze(
            stock_id=uuid4(),
            timeframe=Timeframe.DAILY,
            price_bars=[],
            current_period=None,
            previous_period=None,
            momentum_lookback=5,
            volume_lookback=5,
        )

    assert result.data_timestamp is None
