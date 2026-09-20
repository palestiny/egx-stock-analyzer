from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.application.analysis.daily_market_analysis import StockAnalysisInput, StockAnalysisResult
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.application.reporting.calculate_snapshot_performance import CalculateSnapshotPerformance
from app.application.reporting.change_detection import DetectAnalysisChanges
from app.application.analysis.get_market_opportunity_ranking import GetMarketOpportunityRanking
from app.application.analysis.get_analysis_run import GetAnalysisRun
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.application.analysis.run_market_analysis import RunMarketAnalysis
from app.application.analysis.rank_market_opportunities import RankMarketOpportunities
from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol
from app.application.analysis.runtime import StockAnalysisRuntime, create_stock_analysis_runtime
from app.application.execution.retry import RetryPolicy
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.stocks.stock import Stock


class FakeInputAssembler:
    def assemble(self, stock: Stock, as_of: date) -> StockAnalysisInput:
        period = FinancialPeriod(
            period_end=date(2026, 6, 30),
            revenue=Decimal("100"),
            net_income=Decimal("10"),
        )
        return StockAnalysisInput(
            symbol=stock.symbol,
            stock_id=stock.id,
            timeframe=stock_analysis_timeframe(),
            price_bars=[],
            current_period=period,
            previous_period=period,
            momentum_lookback=5,
            volume_lookback=5,
        )


def stock_analysis_timeframe():
    from app.domain.market_data.timeframe import Timeframe

    return Timeframe.DAILY


def test_create_stock_analysis_runtime_wires_symbol_use_case_and_store() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    runtime = create_stock_analysis_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        input_assembler=FakeInputAssembler(),
        result_store=store,
        retry_policy=RetryPolicy(1),
    )

    assert isinstance(runtime, StockAnalysisRuntime)
    assert isinstance(runtime.run_by_symbol, RunStockAnalysisBySymbol)
    assert isinstance(runtime.run_market_analysis, RunMarketAnalysis)
    assert isinstance(runtime.run_configured_market_analysis, RunConfiguredMarketAnalysis)
    assert isinstance(runtime.rank_market_opportunities, RankMarketOpportunities)
    assert isinstance(runtime.get_market_opportunity_ranking, GetMarketOpportunityRanking)
    assert isinstance(runtime.get_analysis_run, GetAnalysisRun)
    assert isinstance(runtime.run_stock_analysis, RunStockAnalysis)
    assert isinstance(runtime.get_analysis_history, GetAnalysisHistory)
    assert isinstance(runtime.detect_analysis_changes, DetectAnalysisChanges)
    assert isinstance(runtime.calculate_snapshot_performance, CalculateSnapshotPerformance)
    assert runtime.result_store is store


def test_runtime_exposes_shared_analysis_dependencies() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store = InMemoryAnalysisResultStore()
    runtime = create_stock_analysis_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        input_assembler=FakeInputAssembler(),
        result_store=store,
        retry_policy=RetryPolicy(1),
    )

    assert runtime.result_store is store
    assert runtime.run_by_symbol is not None
    assert runtime.run_market_analysis is not None
    assert runtime.run_configured_market_analysis is not None
    assert runtime.rank_market_opportunities is not None
    assert runtime.get_market_opportunity_ranking is not None
    assert runtime.get_analysis_run is not None
    assert runtime.run_stock_analysis is not None
    assert runtime.detect_analysis_changes is not None
    assert runtime.calculate_snapshot_performance is not None
