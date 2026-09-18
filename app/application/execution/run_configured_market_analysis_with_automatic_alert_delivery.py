from dataclasses import dataclass
from datetime import date

from app.application.analysis.run_configured_market_analysis import (
    RunConfiguredMarketAnalysis,
)
from app.application.notifications.automatic_alert_delivery import (
    AutomaticAlertDelivery,
    AutomaticAlertDeliveryResult,
)
from app.domain.execution import Execution


@dataclass(frozen=True)
class ConfiguredMarketAnalysisDeliveryResult:
    analysis_execution: Execution
    delivery_result: AutomaticAlertDeliveryResult


class RunConfiguredMarketAnalysisWithAutomaticAlertDelivery:
    """Compose configured-market analysis with post-analysis alert delivery."""

    def __init__(
        self,
        run_configured_market_analysis: RunConfiguredMarketAnalysis,
        automatic_alert_delivery: AutomaticAlertDelivery,
    ) -> None:
        self._run_configured_market_analysis = run_configured_market_analysis
        self._automatic_alert_delivery = automatic_alert_delivery

    def execute(self, as_of: date) -> ConfiguredMarketAnalysisDeliveryResult:
        analysis_execution = self._run_configured_market_analysis.execute(as_of)
        delivery_result = self._automatic_alert_delivery.execute(analysis_execution)

        return ConfiguredMarketAnalysisDeliveryResult(
            analysis_execution=analysis_execution,
            delivery_result=delivery_result,
        )
