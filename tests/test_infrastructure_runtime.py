from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.runtime import StockAnalysisRuntime
from app.application.execution.retry import RetryPolicy
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.market_data.yahoo_finance import (
    YahooFinanceAdapter,
    YahooFinanceFundamentalDataSource,
)
from app.infrastructure.runtime import InfrastructureRuntime, create_infrastructure_runtime


class FakeYFinanceModule:
    pass


def test_create_infrastructure_runtime_composes_real_adapters() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")

    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(),
        result_store=InMemoryAnalysisResultStore(),
        retry_policy=RetryPolicy(1),
    )

    assert isinstance(runtime, InfrastructureRuntime)
    assert isinstance(runtime.application_runtime, StockAnalysisRuntime)
    assert isinstance(runtime.market_data_provider, YahooFinanceAdapter)
    assert isinstance(
        runtime.fundamental_data_provider,
        YahooFinanceFundamentalDataSource,
    )

    runtime.close()


def test_infrastructure_runtime_owns_shared_result_store() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")
    result_store = InMemoryAnalysisResultStore()

    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(),
        result_store=result_store,
        retry_policy=RetryPolicy(1),
    )

    assert runtime.application_runtime.result_store is result_store
    runtime.close()
