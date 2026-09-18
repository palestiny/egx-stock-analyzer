from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.application.analysis.daily_market_analysis import StockAnalysisInput
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.execution.retry import RetryPolicy
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


class FakeInputAssembler:
    def __init__(self, analysis_input: StockAnalysisInput) -> None:
        self.analysis_input = analysis_input
        self.calls: list[tuple[Stock, date]] = []

    def assemble(self, stock: Stock, as_of: date) -> StockAnalysisInput:
        self.calls.append((stock, as_of))
        return self.analysis_input


def make_input(stock: Stock) -> StockAnalysisInput:
    period = FinancialPeriod(
        period_end=date(2026, 6, 30),
        revenue=Decimal("100"),
        net_income=Decimal("10"),
    )
    previous_period = FinancialPeriod(
        period_end=date(2026, 3, 31),
        revenue=Decimal("90"),
        net_income=Decimal("8"),
    )
    return StockAnalysisInput(
        symbol=stock.symbol,
        stock_id=stock.id,
        timeframe=Timeframe.DAILY,
        price_bars=[],
        current_period=period,
        previous_period=previous_period,
        momentum_lookback=5,
        volume_lookback=5,
    )


def test_run_stock_analysis_assembles_runs_and_stores_result():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    analysis_input = make_input(stock)
    assembler = FakeInputAssembler(analysis_input)
    store = InMemoryAnalysisResultStore()
    expected_result = object()

    with patch(
        "app.application.analysis.daily_market_analysis.StockAnalysisPipeline.analyze",
        return_value=expected_result,
    ):
        RunStockAnalysis(assembler, store, RetryPolicy(1)).execute(
            stock,
            date(2026, 9, 16),
        )

    assert assembler.calls == [(stock, date(2026, 9, 16))]
    assert store.get("EGAL") is expected_result
    record = store.get_record("EGAL")
    assert record is not None
    assert record.analysis_date == date(2026, 9, 16)


def test_run_stock_analysis_includes_failure_reason():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    assembler = FakeInputAssembler(make_input(stock))
    store = InMemoryAnalysisResultStore()

    with patch(
        "app.application.analysis.daily_market_analysis.StockAnalysisPipeline.analyze",
        side_effect=ValueError("invalid analysis input"),
    ):
        try:
            RunStockAnalysis(assembler, store, RetryPolicy(1)).execute(
                stock,
                date(2026, 9, 16),
            )
        except RuntimeError as error:
            assert "invalid analysis input" in str(error)
        else:
            raise AssertionError("Expected RuntimeError")
