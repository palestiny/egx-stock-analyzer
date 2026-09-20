from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from app.application.analysis.list_analysis_runs import AnalysisRunListView


@dataclass(frozen=True)
class AnalysisRunListItemResponse:
    run_id: UUID
    created_at: datetime
    state: str


@dataclass(frozen=True)
class AnalysisRunListResponse:
    items: tuple[AnalysisRunListItemResponse, ...]
    has_more: bool
    next_cursor: str | None

    @classmethod
    def from_view(cls, view: AnalysisRunListView) -> "AnalysisRunListResponse":
        return cls(
            items=tuple(
                AnalysisRunListItemResponse(
                    run_id=item.run_id,
                    created_at=item.created_at,
                    state=item.state.value,
                )
                for item in view.items
            ),
            has_more=view.next_cursor is not None,
            next_cursor=view.next_cursor,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
