from dataclasses import dataclass, field

from app.application.analysis.input_assembler import AnalysisInputAssembler
from app.application.analysis.result_store import (
    AnalysisResultStore,
    InMemoryAnalysisResultStore,
)
from app.application.analysis.runtime import (
    StockAnalysisRuntime,
    create_stock_analysis_runtime,
)
from app.application.execution.retry import RetryPolicy
from app.application.stocks.catalog import StockCatalog
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.market_data.yahoo_finance import (
    YahooFinanceAdapter,
    YahooFinanceFundamentalDataSource,
    YahooFinanceHistoryClient,
 )
from app.infrastructure.persistence.sqlite_analysis_result_store import (
    SQLiteAnalysisResultStore,
)


@dataclass
class InfrastructureRuntime:
    application_runtime: StockAnalysisRuntime
    market_data_provider: YahooFinanceAdapter
    fundamental_data_provider: YahooFinanceFundamentalDataSource
    _closed: bool = field(default=False, init=False, repr=False)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        self.fundamental_data_provider.close()
        self._closed = True


def create_infrastructure_runtime(
    stock_catalog: StockCatalog,
    yfinance_module,
    config: InfrastructureConfig,
    result_store: AnalysisResultStore | None = None,
    retry_policy: RetryPolicy | None = None,
) -> InfrastructureRuntime:
    result_store = result_store or SQLiteAnalysisResultStore(config.analysis_database_path)
    retry_policy = retry_policy or RetryPolicy(1)

    yahoo_history_client = YahooFinanceHistoryClient(yfinance_module)
    market_data_provider = YahooFinanceAdapter(yahoo_history_client)
    fundamental_data_provider = YahooFinanceFundamentalDataSource(yfinance_module)

    input_assembler = AnalysisInputAssembler(
        market_data_provider=market_data_provider,
        fundamental_data_provider=fundamental_data_provider,
    )

    application_runtime = create_stock_analysis_runtime(
        stock_catalog=stock_catalog,
        input_assembler=input_assembler,
        result_store=result_store,
        retry_policy=retry_policy,
    )

    return InfrastructureRuntime(
        application_runtime=application_runtime,
        market_data_provider=market_data_provider,
        fundamental_data_provider=fundamental_data_provider,
    )
