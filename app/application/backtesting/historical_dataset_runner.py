from dataclasses import replace
from datetime import date

from app.application.clock import EGX_TIMEZONE

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
        *,
        evaluation_start_date: date | None = None,
    ) -> BacktestResult:
        if from_date > to_date:
            raise ValueError("from_date cannot be after to_date")
        evaluation_start = evaluation_start_date or from_date
        if not from_date <= evaluation_start <= to_date:
            raise ValueError(
                "evaluation_start_date must be between from_date and to_date"
            )

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

        evaluation_start_index = next(
            (
                index
                for index, bar in enumerate(price_bars)
                if bar.timestamp.astimezone(EGX_TIMEZONE).date() >= evaluation_start
            ),
            None,
        )
        if evaluation_start_index is None:
            raise ValueError(
                "No valid market bars on or after evaluation_start_date"
            )

        # Historical bars before the evaluation start seed indicators and
        # point-in-time analysis, but they must not generate evaluation trades.
        effective_configuration = replace(
            configuration,
            warmup_bars=max(configuration.warmup_bars, evaluation_start_index),
        )
        return BacktestSimulator.run(
            price_bars,
            strategy,
            effective_configuration,
        )
