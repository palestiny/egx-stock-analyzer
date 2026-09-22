from datetime import date

from app.application.analysis.input_assembler import AnalysisInputAssemblyPolicy, AnalysisInputAssembler
from app.application.backtesting.historical_opportunity_strategy import (
    HistoricalOpportunityClassificationBacktestStrategy,
)
from app.application.fundamental_data.historical_provider import PointInTimeFundamentalDataProvider
from app.application.market_data.provider import MarketDataProvider
from app.domain.backtesting.simulator import BacktestConfiguration, BacktestResult, BacktestSimulator
from app.domain.stocks.stock import Stock
from app.infrastructure.historical_dataset.financial_source import HistoricalDatasetFundamentalSnapshotSource
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader
from app.infrastructure.historical_dataset.market_provider import HistoricalDatasetMarketDataProvider


class HistoricalDatasetBacktestRunner:
    """Runs Strategy v0 against the versioned dataset through production input boundaries."""

    def __init__(
        self,
        stock: Stock,
        loader: HistoricalDatasetLoader,
        policy: AnalysisInputAssemblyPolicy | None = None,
    ) -> None:
        self._stock = stock
        self._loader = loader
        self._policy = policy or AnalysisInputAssemblyPolicy()

    def run(
        self,
        from_date: date,
        to_date: date,
        configuration: BacktestConfiguration,
    ) -> BacktestResult:
        market_provider: MarketDataProvider = HistoricalDatasetMarketDataProvider(self._loader)
        observations = market_provider.get_daily_observations(
            self._stock,
            from_date,
            to_date,
        )
        price_bars = AnalysisInputAssembler.build_price_bars(
            observations,
            minimum_price_bars=self._policy.minimum_price_bars,
        )

        fundamental_source = HistoricalDatasetFundamentalSnapshotSource(self._loader)
        fundamental_provider = PointInTimeFundamentalDataProvider(fundamental_source)
        strategy = HistoricalOpportunityClassificationBacktestStrategy(
            stock=self._stock,
            fundamental_data_provider=fundamental_provider,
            policy=self._policy,
        ).to_backtest_strategy()

        return BacktestSimulator.run(price_bars, strategy, configuration)
