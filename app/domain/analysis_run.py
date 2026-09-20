from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.execution import ExecutionState


@dataclass(frozen=True)
class AnalysisRun:
    id: UUID
    created_at: datetime
    state: ExecutionState

    @classmethod
    def create(cls) -> "AnalysisRun":
        return cls(
            id=uuid4(),
            created_at=datetime.now(timezone.utc),
            state=ExecutionState.CREATED,
        )

    def with_state(self, state: ExecutionState) -> "AnalysisRun":
        return AnalysisRun(
            id=self.id,
            created_at=self.created_at,
            state=state,
        )
