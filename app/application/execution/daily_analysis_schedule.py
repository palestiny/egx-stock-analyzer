from datetime import datetime

from app.application.analysis.daily_market_analysis import StockAnalysisInput
from app.application.execution.scheduled_trigger import ScheduledAnalysisTrigger


class DailyAnalysisSchedule:
    def __init__(self, trigger: ScheduledAnalysisTrigger) -> None:
        self._trigger = trigger

    def register(
        self,
        inputs: list[StockAnalysisInput],
        run_at: datetime,
    ) -> None:
        self._trigger.schedule(inputs, run_at)
