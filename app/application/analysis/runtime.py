from dataclasses import dataclass

from app.application.analysis.input_assembler import AnalysisInputAssembler
from app.application.analysis.result_store import AnalysisResultStore
from app.application.analysis.run_stock_analysis import RunStockAnalysis
from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol
from app.application.execution.retry import RetryPolicy
from app.application.stocks.catalog import StockCatalog


@dataclass(frozen=True)
class StockAnalysisRuntime:
    run_by_symbol: RunStockAnalysisBySymbol
    run_stock_analysis: RunStockAnalysis
    result_store: AnalysisResultStore


def create_stock_analysis_runtime(
    stock_catalog: StockCatalog,
    input_assembler: AnalysisInputAssembler,
    result_store: AnalysisResultStore,
    retry_policy: RetryPolicy,
) -> StockAnalysisRuntime:
    run_stock_analysis = RunStockAnalysis(
        input_assembler=input_assembler,
        result_store=result_store,
        retry_policy=retry_policy,
    )
    run_by_symbol = RunStockAnalysisBySymbol(
        stock_catalog=stock_catalog,
        run_stock_analysis=run_stock_analysis,
    )

    return StockAnalysisRuntime(
        run_by_symbol=run_by_symbol,
        run_stock_analysis=run_stock_analysis,
        result_store=result_store,
    )
