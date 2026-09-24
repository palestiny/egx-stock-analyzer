from datetime import date
from typing import Callable

from app.application.analysis.input_assembler import AnalysisInputAssemblyPolicy
from app.application.analysis.stock_analysis import StockAnalysisPipeline, StockAnalysisResult
from app.application.fundamental_data.provider import FundamentalDataProvider
from app.domain.backtesting.simulator import BacktestStrategy
from app.domain.market_data.price_bar import PriceBar
from app.domain.stocks.stock import Stock
from app.domain.opportunity.classification import OpportunityClassification


class HistoricalOpportunityClassificationBacktestStrategy:
    """Builds point-in-time production analysis from the simulator's completed-bar history."""

    strategy_id = "opportunity-classification"
    version = "0"

    def __init__(
        self,
        stock: Stock,
        fundamental_data_provider: FundamentalDataProvider,
        policy: AnalysisInputAssemblyPolicy | None = None,
        analyze: Callable[..., StockAnalysisResult] = StockAnalysisPipeline.analyze,
    ) -> None:
        self._stock = stock
        self._fundamental_data_provider = fundamental_data_provider
        self._policy = policy or AnalysisInputAssemblyPolicy()
        self._analyze = analyze

    def to_backtest_strategy(self) -> BacktestStrategy:
        def analyze_history(history: list[PriceBar]) -> StockAnalysisResult:
            if len(history) < self._policy.minimum_price_bars:
                raise ValueError(
                    "Historical analysis requires at least "
                    f"{self._policy.minimum_price_bars} completed price bars"
                )

            as_of = self._as_of(history[-1])
            current_period, previous_period = self._fundamental_data_provider.get_periods(
                self._stock,
                as_of,
            )

            return self._analyze(
                self._stock.id,
                self._policy.timeframe,
                history,
                current_period,
                previous_period,
                self._policy.momentum_lookback,
                self._policy.volume_lookback,
            )

        def is_buy(history: list[PriceBar]) -> bool:
            if len(history) < self._policy.minimum_price_bars:
                return False
            result = analyze_history(history)
            return result.opportunity.classification is OpportunityClassification.BUY

        return BacktestStrategy(
            strategy_id=self.strategy_id,
            version=self.version,
            signal=is_buy,
            position_valid=is_buy,
        )

    @staticmethod
    def _as_of(bar: PriceBar) -> date:
        return bar.timestamp.date()
