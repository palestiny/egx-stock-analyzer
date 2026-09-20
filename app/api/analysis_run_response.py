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
class AnalysisRunResponse:
    run_id: UUID
    created_at: datetime
    state: str
    snapshots: tuple[AnalysisRunSnapshotResponse, ...]
    next_cursor: str | None

    @classmethod
    def from_view(cls, view: AnalysisRunView) -> "AnalysisRunResponse":
        return cls(
            run_id=view.run_id,
            created_at=view.created_at,
            state=view.state.value,
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
