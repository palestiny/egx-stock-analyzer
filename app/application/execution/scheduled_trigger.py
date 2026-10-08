from datetime import datetime

from app.application.analysis.daily_market_analysis import (
    DailyMarketAnalysis,
    StockAnalysisInput,
)
from app.application.execution.scheduler import Scheduler
from app.domain.execution import Execution


class ScheduledAnalysisTrigger:
    def __init__(
        self,
        analysis: DailyMarketAnalysis,
        scheduler: Scheduler,
    ) -> None:
        self._analysis = analysis
        self._scheduler = scheduler

    def schedule(
        self,
        inputs: list[StockAnalysisInput],
        run_at: datetime,
    ) -> None:
        def operation() -> Execution:
            return self._analysis.run(inputs).execution

        self._scheduler.schedule(operation, run_at)
