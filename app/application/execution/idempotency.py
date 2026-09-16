from dataclasses import dataclass
from datetime import date

from app.domain.execution import Execution


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

        if existing is not None:
            if existing.state in {
                existing.state.RUNNING,
                existing.state.COMPLETED,
            }:
                return existing

        execution = Execution.create()
        self._executions[identity] = execution
        return execution
