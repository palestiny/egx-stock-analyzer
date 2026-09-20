from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.domain.execution import ExecutionState


MAX_FAILURE_DETAIL_LENGTH = 240


class AnalysisRunOutcomeState(Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class AnalysisRunOutcome:
    symbol: str
    state: AnalysisRunOutcomeState
    stock_id: UUID | None = None
    failure_code: str | None = None
    failure_detail: str | None = None

    @classmethod
    def success(cls, symbol: str, stock_id: UUID | None = None) -> "AnalysisRunOutcome":
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("Analysis run outcome symbol cannot be empty")
        return cls(
            symbol=normalized_symbol,
            state=AnalysisRunOutcomeState.SUCCESS,
            stock_id=stock_id,
        )

    @classmethod
    def failed(
        cls,
        symbol: str,
        failure_code: str,
        failure_detail: str | None = None,
        stock_id: UUID | None = None,
    ) -> "AnalysisRunOutcome":
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("Analysis run outcome symbol cannot be empty")
        normalized_code = failure_code.strip().upper()
        if not normalized_code:
            raise ValueError("Analysis run outcome failure code cannot be empty")
        safe_detail = failure_detail.strip() if failure_detail else None
        if safe_detail:
            safe_detail = safe_detail[:MAX_FAILURE_DETAIL_LENGTH]
        return cls(
            symbol=normalized_symbol,
            state=AnalysisRunOutcomeState.FAILED,
            stock_id=stock_id,
            failure_code=normalized_code,
            failure_detail=safe_detail,
        )


@dataclass(frozen=True)
class AnalysisRun:
    id: UUID
    created_at: datetime
    state: ExecutionState
    owner_user_id: UUID | None = None
    outcomes: tuple[AnalysisRunOutcome, ...] = ()
    outcomes_available: bool = False

    @classmethod
    def create(cls, owner_user_id: UUID | None = None) -> "AnalysisRun":
        return cls(
            id=uuid4(),
            created_at=datetime.now(timezone.utc),
            state=ExecutionState.CREATED,
            owner_user_id=owner_user_id,
        )

    def with_state(self, state: ExecutionState) -> "AnalysisRun":
        return AnalysisRun(
            id=self.id,
            created_at=self.created_at,
            state=state,
            owner_user_id=self.owner_user_id,
            outcomes=self.outcomes,
            outcomes_available=self.outcomes_available,
        )

    def with_outcomes(
        self,
        outcomes: tuple[AnalysisRunOutcome, ...],
    ) -> "AnalysisRun":
        normalized = tuple(outcomes)
        seen: set[str] = set()
        for outcome in normalized:
            if outcome.symbol in seen:
                raise ValueError(
                    f"Duplicate analysis run outcome symbol: {outcome.symbol}"
                )
            seen.add(outcome.symbol)
        return AnalysisRun(
            id=self.id,
            created_at=self.created_at,
            state=self.state,
            owner_user_id=self.owner_user_id,
            outcomes=normalized,
            outcomes_available=True,
        )
