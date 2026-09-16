from collections.abc import Callable

from app.application.analysis.daily_market_analysis import (
    DailyMarketAnalysis,
    StockAnalysisInput,
)
from app.domain.execution import Execution


class ScheduledAnalysisTrigger:
    def __init__(
        self,
        analysis: DailyMarketAnalysis,
        scheduler: object,
    ) -> None:
        self._analysis = analysis
        self._scheduler = scheduler

    def schedule(self, inputs: list[StockAnalysisInput]) -> None:
        operation: Callable[[], Execution] = lambda: self._analysis.run(inputs).execution
        self._scheduler.schedule(operation)
