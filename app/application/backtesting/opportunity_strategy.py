from collections.abc import Callable

from app.application.analysis.stock_analysis import StockAnalysisResult
from app.domain.backtesting.simulator import BacktestStrategy
from app.domain.market_data.price_bar import PriceBar
from app.domain.opportunity.classification import OpportunityClassification


class OpportunityClassificationBacktestStrategy:
    strategy_id = "opportunity-classification"
    version = "0"

    def __init__(
        self,
        analyze: Callable[[list[PriceBar]], StockAnalysisResult],
    ) -> None:
        self._analyze = analyze

    def to_backtest_strategy(self) -> BacktestStrategy:
        def is_buy(history: list[PriceBar]) -> bool:
            result = self._analyze(history)
            return result.opportunity.classification is OpportunityClassification.BUY

        return BacktestStrategy(
            strategy_id=self.strategy_id,
            version=self.version,
            signal=is_buy,
            position_valid=is_buy,
        )
