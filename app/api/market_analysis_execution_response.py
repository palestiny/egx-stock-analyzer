from dataclasses import dataclass
from uuid import UUID

from app.application.analysis.run_configured_market_analysis_with_automatic_alerts import ConfiguredMarketAnalysisResult


@dataclass(frozen=True)
class MarketAnalysisExecutionResponse:
    execution_id: UUID
    state: str
    successful_stock_ids: list[str]
    failed_stock_ids: list[str]
    failure_reasons: dict[str, str]
    automatic_alert_delivery: dict[str, object] | None

    @classmethod
    def from_result(
        cls,
        result: ConfiguredMarketAnalysisResult,
    ) -> "MarketAnalysisExecutionResponse":
        return cls(
            execution_id=result.execution.id,
            state=result.execution.state.value,
            successful_stock_ids=sorted(result.execution.successful_stock_ids),
            failed_stock_ids=sorted(result.execution.failed_stock_ids),
            failure_reasons=dict(sorted(result.execution.failure_reasons.items())),
            automatic_alert_delivery=(
                None
                if result.automatic_alert_delivery is None
                else {
                    "state": result.automatic_alert_delivery.state.value,
                    "attempted_count": result.automatic_alert_delivery.attempted_count,
                    "delivered_count": result.automatic_alert_delivery.delivered_count,
                    "skipped_count": result.automatic_alert_delivery.skipped_count,
                    "failed_count": result.automatic_alert_delivery.failed_count,
                    "failure_reasons": dict(
                        sorted(result.automatic_alert_delivery.failure_reasons.items())
                    ),
                }
            ),
        )
