from dataclasses import asdict, dataclass
from datetime import date, datetime
from uuid import UUID

from app.application.analysis.get_analysis_run import AnalysisRunView


@dataclass(frozen=True)
class AnalysisRunSnapshotResponse:
    snapshot_id: UUID
    symbol: str
    analysis_date: date | None


@dataclass(frozen=True)
class AnalysisRunOutcomeResponse:
    symbol: str
    state: str
    stock_id: UUID | None
    failure_code: str | None
    failure_detail: str | None


@dataclass(frozen=True)
class AnalysisRunResponse:
    run_id: UUID
    created_at: datetime
    state: str
    outcomes_available: bool
    outcomes: tuple[AnalysisRunOutcomeResponse, ...]
    snapshots: tuple[AnalysisRunSnapshotResponse, ...]
    next_cursor: str | None

    @classmethod
    def from_view(cls, view: AnalysisRunView) -> "AnalysisRunResponse":
        return cls(
            run_id=view.run_id,
            created_at=view.created_at,
            state=view.state.value,
            outcomes_available=view.outcomes_available,
            outcomes=tuple(
                AnalysisRunOutcomeResponse(
                    symbol=item.symbol,
                    state=item.state,
                    stock_id=item.stock_id,
                    failure_code=item.failure_code,
                    failure_detail=item.failure_detail,
                )
                for item in view.outcomes
            ),
            snapshots=tuple(
                AnalysisRunSnapshotResponse(
                    snapshot_id=item.snapshot_id,
                    symbol=item.symbol,
                    analysis_date=item.analysis_date,
                )
                for item in view.snapshots
            ),
            next_cursor=view.next_cursor,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
