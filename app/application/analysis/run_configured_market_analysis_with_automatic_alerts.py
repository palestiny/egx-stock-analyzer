from dataclasses import dataclass
from datetime import date

from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.application.notifications.automatic_alert_delivery import (
    AutomaticAlertDelivery,
    AutomaticAlertDeliveryResult,
)
from app.domain.execution import Execution, ExecutionState


@dataclass(frozen=True)
class ConfiguredMarketAnalysisResult:
    execution: Execution
    automatic_alert_delivery: AutomaticAlertDeliveryResult | None


class RunConfiguredMarketAnalysisWithAutomaticAlerts:
    def __init__(
        self,
        run_configured_market_analysis: RunConfiguredMarketAnalysis,
        automatic_alert_delivery: AutomaticAlertDelivery | None = None,
    ) -> None:
        self._run_configured_market_analysis = run_configured_market_analysis
        self._automatic_alert_delivery = automatic_alert_delivery

    def execute(self, as_of: date) -> ConfiguredMarketAnalysisResult:
        execution = self._run_configured_market_analysis.execute(as_of)

        if (
            self._automatic_alert_delivery is None
            or execution.state is ExecutionState.FAILED
        ):
            return ConfiguredMarketAnalysisResult(
                execution=execution,
                automatic_alert_delivery=None,
            )

        delivery = self._automatic_alert_delivery.execute(execution)
        return ConfiguredMarketAnalysisResult(
            execution=execution,
            automatic_alert_delivery=delivery,
        )
