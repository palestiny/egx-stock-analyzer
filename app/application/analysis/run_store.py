from datetime import datetime
from typing import Protocol
from uuid import UUID



from app.domain.analysis_run import AnalysisRun
from app.domain.execution import ExecutionState


class AnalysisRunStore(Protocol):
    def save(self, run: AnalysisRun) -> None:
        ...

    def get(self, run_id: UUID) -> AnalysisRun | None:
        ...

    def list_runs(
        self,
        *,
        state: ExecutionState | None = None,
        owner_user_id: UUID | None = None,
        include_global: bool = False,
        before_created_at: datetime | None = None,
        before_run_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[AnalysisRun, ...]:
        ...


class InMemoryAnalysisRunStore:
    def __init__(self) -> None:
        self._runs: dict[UUID, AnalysisRun] = {}

    def save(self, run: AnalysisRun) -> None:
        self._runs[run.id] = run

    def get(self, run_id: UUID) -> AnalysisRun | None:
        return self._runs.get(run_id)

    def list_runs(
        self,
        *,
        state: ExecutionState | None = None,
        owner_user_id: UUID | None = None,
        include_global: bool = False,
        before_created_at: datetime | None = None,
        before_run_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[AnalysisRun, ...]:
        runs = [
            run
            for run in self._runs.values()
            if (state is None or run.state is state)
            and (
                owner_user_id is None
                or run.owner_user_id == owner_user_id
                or (include_global and run.owner_user_id is None)
            )
        ]
        runs.sort(key=lambda run: (run.created_at, str(run.id)), reverse=True)

        if before_created_at is not None and before_run_id is not None:
            runs = [
                run
                for run in runs
                if (run.created_at, str(run.id))
                < (before_created_at, str(before_run_id))
            ]

        return tuple(runs[:limit])
