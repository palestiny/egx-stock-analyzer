from unittest.mock import patch

from app.application.analysis.daily_market_analysis import DailyMarketAnalysis
from app.application.execution.retry import RetryPolicy
from app.domain.execution import ExecutionState


def test_daily_market_analysis_runs_all_stocks_and_collects_results():
    expected_results = {
        "EGAL": object(),
        "IEEC": object(),
    }

    with patch(
        "app.application.analysis.daily_market_analysis.StockAnalysisPipeline.analyze",
        side_effect=lambda stock_id: expected_results[stock_id],
    ):
        result = DailyMarketAnalysis(RetryPolicy(max_attempts=1)).run(
            ["EGAL", "IEEC"],
        )

    assert result.execution.state == ExecutionState.COMPLETED
    assert result.execution.successful_stock_ids == {"EGAL", "IEEC"}
    assert result.execution.failed_stock_ids == set()
    assert result.stock_results == expected_results


def test_daily_market_analysis_continues_after_one_stock_fails():
    expected_egal_result = object()

    def analyze(stock_id: str):
        if stock_id == "IEEC":
            raise ValueError("analysis failed")
        return expected_egal_result

    with patch(
        "app.application.analysis.daily_market_analysis.StockAnalysisPipeline.analyze",
        side_effect=analyze,
    ):
        result = DailyMarketAnalysis(RetryPolicy(max_attempts=1)).run(
            ["EGAL", "IEEC"],
        )

    assert result.execution.state == ExecutionState.COMPLETED_WITH_ERRORS
    assert result.execution.successful_stock_ids == {"EGAL"}
    assert result.execution.failed_stock_ids == {"IEEC"}
    assert result.stock_results == {"EGAL": expected_egal_result}
