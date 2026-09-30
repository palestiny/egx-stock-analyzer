from datetime import date

from app.application.analysis.input_assembler import AnalysisInputAssemblyPolicy, AnalysisInputAssembler
from app.application.backtesting.historical_opportunity_strategy import (
    HistoricalOpportunityClassificationBacktestStrategy,
)
from app.application.fundamental_data.historical_provider import (
    HistoricalFundamentalSnapshotSource,
    PointInTimeFundamentalDataProvider,
)
from app.application.market_data.provider import MarketDataProvider
from app.domain.backtesting.simulator import BacktestConfiguration, BacktestResult, BacktestSimulator
from app.domain.stocks.stock import Stock


class HistoricalDatasetBacktestRunner:
    """Runs Strategy v0 through application-facing historical data contracts."""

    def __init__(
        self,
        stock: Stock,
        market_data_provider: MarketDataProvider,
        fundamental_snapshot_source: HistoricalFundamentalSnapshotSource,
        policy: AnalysisInputAssemblyPolicy | None = None,
    ) -> None:
        self._stock = stock
        self._market_data_provider = market_data_provider
        self._fundamental_snapshot_source = fundamental_snapshot_source
        self._policy = policy or AnalysisInputAssemblyPolicy()

    def run(
        self,
        from_date: date,
        to_date: date,
        configuration: BacktestConfiguration,
    ) -> BacktestResult:
        observations = self._market_data_provider.get_daily_observations(
            self._stock,
            from_date,
            to_date,
        )
        price_bars = AnalysisInputAssembler.build_price_bars(
            observations,
            minimum_price_bars=self._policy.minimum_price_bars,
        )

        fundamental_provider = PointInTimeFundamentalDataProvider(
            self._fundamental_snapshot_source
        )
        strategy = HistoricalOpportunityClassificationBacktestStrategy(
            stock=self._stock,
            fundamental_data_provider=fundamental_provider,
            policy=self._policy,
        ).to_backtest_strategy()

        return BacktestSimulator.run(price_bars, strategy, configuration)
