from typing import Protocol
from uuid import UUID

from app.domain.analysis_run import AnalysisRun


class AnalysisRunStore(Protocol):
    def save(self, run: AnalysisRun) -> None:
        ...

    def get(self, run_id: UUID) -> AnalysisRun | None:
        ...


class InMemoryAnalysisRunStore:
    def __init__(self) -> None:
        self._runs: dict[UUID, AnalysisRun] = {}

    def save(self, run: AnalysisRun) -> None:
        self._runs[run.id] = run

    def get(self, run_id: UUID) -> AnalysisRun | None:
        return self._runs.get(run_id)
