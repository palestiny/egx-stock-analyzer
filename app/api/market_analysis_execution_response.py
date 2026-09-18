from dataclasses import dataclass
from uuid import UUID

from app.domain.execution import Execution


@dataclass(frozen=True)
class MarketAnalysisExecutionResponse:
    execution_id: UUID
    state: str
    successful_stock_ids: list[str]
    failed_stock_ids: list[str]
    failure_reasons: dict[str, str]

    @classmethod
    def from_execution(
        cls,
        execution: Execution,
    ) -> "MarketAnalysisExecutionResponse":
        return cls(
            execution_id=execution.id,
            state=execution.state.value,
            successful_stock_ids=sorted(execution.successful_stock_ids),
            failed_stock_ids=sorted(execution.failed_stock_ids),
            failure_reasons=dict(sorted(execution.failure_reasons.items())),
        )
