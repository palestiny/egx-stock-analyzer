from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.application.analysis.daily_market_analysis import (
    DailyMarketAnalysis,
    StockAnalysisInput,
)
from app.application.execution.retry import RetryPolicy
from app.domain.execution import ExecutionState
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.timeframe import Timeframe


def make_input(symbol: str) -> StockAnalysisInput:
    return StockAnalysisInput(
        symbol=symbol,
        stock_id=uuid4(),
        timeframe=Timeframe.DAILY,
        price_bars=[],
        current_period=FinancialPeriod(
            period_end=date(2026, 9, 15),
            revenue=Decimal("100"),
            net_income=Decimal("10"),
        ),
        previous_period=FinancialPeriod(
            period_end=date(2026, 6, 30),
            revenue=Decimal("90"),
            net_income=Decimal("8"),
        ),
        momentum_lookback=5,
        volume_lookback=5,
    )


def test_daily_market_analysis_runs_all_stocks_and_collects_results():
    inputs = [make_input("EGAL"), make_input("IEEC")]
    expected_results = {"EGAL": object(), "IEEC": object()}

    def analyze(request: StockAnalysisInput):
        return expected_results[request.symbol]

    with patch(
        "app.application.analysis.daily_market_analysis.StockAnalysisPipeline.analyze",
        side_effect=analyze,
    ) as pipeline:
        result = DailyMarketAnalysis(RetryPolicy(max_attempts=1)).run(inputs)

    assert result.execution.state == ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == {"EGAL", "IEEC"}
    assert result.execution.failed_stock_ids == set()
    assert result.stock_results == expected_results
    assert pipeline.call_count == 2


def test_daily_market_analysis_continues_after_one_stock_fails():
    inputs = [make_input("EGAL"), make_input("IEEC")]
    expected_egal_result = object()

    def analyze(request: StockAnalysisInput):
        if request.symbol == "IEEC":
            raise ValueError("analysis failed")
        return expected_egal_result

    with patch(
        "app.application.analysis.daily_market_analysis.StockAnalysisPipeline.analyze",
        side_effect=analyze,
    ):
        result = DailyMarketAnalysis(RetryPolicy(max_attempts=1)).run(inputs)

    assert result.execution.state == ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert result.execution.failed_stock_ids == {"IEEC"}
    assert result.stock_results == {"EGAL": expected_egal_result}
