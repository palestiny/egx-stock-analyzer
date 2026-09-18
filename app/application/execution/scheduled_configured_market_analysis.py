from datetime import date, datetime
from app.application.analysis.run_configured_market_analysis_with_automatic_alerts import (
    RunConfiguredMarketAnalysisWithAutomaticAlertsWithAutomaticAlerts,
)
from app.application.execution.scheduler import Scheduler
from app.domain.execution import Execution


class ScheduledConfiguredMarketAnalysis:
    """Register configured-market analysis as a one-shot scheduler operation."""

    def __init__(
        self,
        run_configured_market_analysis: RunConfiguredMarketAnalysis,
        scheduler: Scheduler,
    ) -> None:
        self._run_configured_market_analysis = run_configured_market_analysis
        self._scheduler = scheduler

    def schedule(self, run_at: datetime) -> None:
        def operation() -> Execution:
            return self._run_configured_market_analysis.execute(date.today())

        self._scheduler.schedule(operation, run_at)
