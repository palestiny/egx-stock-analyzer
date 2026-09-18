from collections.abc import Callable
from datetime import date, datetime

from app.application.analysis.run_configured_market_analysis import (
    RunConfiguredMarketAnalysis,
)
from app.application.execution.scheduler import Scheduler


class ScheduledConfiguredMarketAnalysis:
    def __init__(
        self,
        run_configured_market_analysis: RunConfiguredMarketAnalysis,
        scheduler: Scheduler,
    ) -> None:
        self._run_configured_market_analysis = run_configured_market_analysis
        self._scheduler = scheduler

    def schedule(self, run_at: datetime) -> None:
        operation: Callable[[], object] = (
            lambda: self._run_configured_market_analysis.execute(date.today())
        )
        self._scheduler.schedule(operation, run_at)
