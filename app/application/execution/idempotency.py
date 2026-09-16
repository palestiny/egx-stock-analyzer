from dataclasses import dataclass
from datetime import date

from app.domain.execution import Execution, ExecutionState


@dataclass(frozen=True)
class ExecutionIdentity:
    analysis_date: date
    analysis_type: str
    strategy_version: str
    configuration: str


class ExecutionRegistry:
    def __init__(self) -> None:
        self._executions: dict[ExecutionIdentity, Execution] = {}

    def create(self, identity: ExecutionIdentity) -> Execution:
        existing = self._executions.get(identity)

        if existing is not None and existing.state in {
            ExecutionState.RUNNING,
            ExecutionState.COMPLETED,
        }:
            return existing

        execution = Execution.create()
        self._executions[identity] = execution
        return execution
