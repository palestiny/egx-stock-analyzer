from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.application.analysis.daily_market_analysis import DailyMarketAnalysis, StockAnalysisInput
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.execution.retry import RetryPolicy
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.timeframe import Timeframe


def make_input(symbol: str) -> StockAnalysisInput:
    return StockAnalysisInput(
        symbol=symbol,
        stock_id=uuid4(),
        timeframe=Timeframe.DAILY,
        price_bars=[],
        current_period=FinancialPeriod(date(2026, 9, 15), Decimal("100"), Decimal("10")),
        previous_period=FinancialPeriod(date(2026, 6, 30), Decimal("90"), Decimal("8")),
        momentum_lookback=5,
        volume_lookback=5,
    )


def test_daily_market_analysis_saves_successful_results_in_store():
    inputs = [make_input("EGAL")]
    expected_result = object()
    store = InMemoryAnalysisResultStore()

    with patch(
        "app.application.analysis.daily_market_analysis.StockAnalysisPipeline.analyze",
        return_value=expected_result,
    ):
        result = DailyMarketAnalysis(RetryPolicy(1), store).run(inputs)

    assert result.stock_results["EGAL"] is expected_result
    assert store.get("EGAL") is expected_result
