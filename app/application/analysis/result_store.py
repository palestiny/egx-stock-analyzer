from dataclasses import dataclass, field
from datetime import date
from typing import Protocol
from uuid import UUID, uuid4

from app.application.analysis.stock_analysis import StockAnalysisResult
from app.domain.execution import ExecutionState


class AnalysisResultPersistenceError(RuntimeError):
    """Raised when analysis-result or run persistence cannot be completed."""


@dataclass(frozen=True)
class AnalysisRunRecord:
    run_id: UUID
    analysis_date: date | None
    state: ExecutionState


@dataclass(frozen=True)
class AnalysisResultRecord:
    result: StockAnalysisResult
    analysis_date: date | None
    snapshot_id: UUID = field(default_factory=uuid4)
    symbol: str | None = None
    analysis_run_id: UUID | None = None


class AnalysisResultStore(Protocol):
    def create_analysis_run(
        self,
        run_id: UUID,
        analysis_date: date | None,
    ) -> None:
        ...

    def update_analysis_run_state(
        self,
        run_id: UUID,
        state: ExecutionState,
    ) -> None:
        ...

    def get_analysis_run(self, run_id: UUID) -> AnalysisRunRecord | None:
        ...

    def save(
        self,
        symbol: str,
        result: StockAnalysisResult,
        analysis_date: date | None = None,
        analysis_run_id: UUID | None = None,
    ) -> None:
        ...

    def get(self, symbol: str) -> StockAnalysisResult | None:
        ...

    def get_record(self, symbol: str) -> AnalysisResultRecord | None:
        ...

    def get_snapshot(self, snapshot_id: UUID) -> AnalysisResultRecord | None:
        ...

    def get_history(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[AnalysisResultRecord, ...]:
        ...

    def get_run_snapshots(
        self,
        run_id: UUID,
    ) -> tuple[AnalysisResultRecord, ...]:
        ...


class InMemoryAnalysisResultStore:
    def __init__(self) -> None:
        self._results: dict[str, list[AnalysisResultRecord]] = {}
        self._analysis_runs: dict[UUID, AnalysisRunRecord] = {}

    def create_analysis_run(
        self,
        run_id: UUID,
        analysis_date: date | None,
    ) -> None:
        if run_id in self._analysis_runs:
            raise AnalysisResultPersistenceError(
                f"Analysis run already exists: {run_id}"
            )
        self._analysis_runs[run_id] = AnalysisRunRecord(
            run_id=run_id,
            analysis_date=analysis_date,
            state=ExecutionState.CREATED,
        )

    def update_analysis_run_state(
        self,
        run_id: UUID,
        state: ExecutionState,
    ) -> None:
        existing = self._analysis_runs.get(run_id)
        if existing is None:
            raise AnalysisResultPersistenceError(
                f"Unknown analysis run: {run_id}"
            )
        self._analysis_runs[run_id] = AnalysisRunRecord(
            run_id=existing.run_id,
            analysis_date=existing.analysis_date,
            state=state,
        )

    def get_analysis_run(self, run_id: UUID) -> AnalysisRunRecord | None:
        return self._analysis_runs.get(run_id)

    def save(
        self,
        symbol: str,
        result: StockAnalysisResult,
        analysis_date: date | None = None,
        analysis_run_id: UUID | None = None,
    ) -> None:
        if analysis_run_id is not None and analysis_run_id not in self._analysis_runs:
            raise AnalysisResultPersistenceError(
                f"Unknown analysis run: {analysis_run_id}"
            )

        if analysis_run_id is not None:
            if any(
                record.analysis_run_id == analysis_run_id
                for records in self._results.values()
                for record in records
                if record.symbol == symbol
            ):
                raise AnalysisResultPersistenceError(
                    f"Snapshot already exists for run {analysis_run_id} and symbol {symbol}"
                )

        records = self._results.setdefault(symbol, [])
        records.append(
            AnalysisResultRecord(
                result=result,
                analysis_date=analysis_date,
                symbol=symbol,
                analysis_run_id=analysis_run_id,
            )
        )

    def get(self, symbol: str) -> StockAnalysisResult | None:
        record = self.get_record(symbol)
        return record.result if record is not None else None

    def get_record(self, symbol: str) -> AnalysisResultRecord | None:
        history = self.get_history(symbol)
        return history[0] if history else None

    def get_snapshot(self, snapshot_id: UUID) -> AnalysisResultRecord | None:
        for records in self._results.values():
            for record in records:
                if record.snapshot_id == snapshot_id:
                    return record
        return None

    def get_history(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[AnalysisResultRecord, ...]:
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

        records = []
        for record in self._results.get(symbol, []):
            if start_date is not None or end_date is not None:
                if record.analysis_date is None:
                    continue
                if start_date is not None and record.analysis_date < start_date:
                    continue
                if end_date is not None and record.analysis_date > end_date:
                    continue
            records.append(record)

        dated_records = sorted(
            (record for record in records if record.analysis_date is not None),
            key=lambda record: record.analysis_date.toordinal(),
            reverse=True,
        )
        undated_records = [
            record for record in records if record.analysis_date is None
        ][::-1]

        return tuple(dated_records + undated_records)

    def get_run_snapshots(
        self,
        run_id: UUID,
    ) -> tuple[AnalysisResultRecord, ...]:
        records = [
            record
            for records in self._results.values()
            for record in records
            if record.analysis_run_id == run_id
        ]
        return tuple(
            sorted(
                records,
                key=lambda record: (
                    record.symbol or "",
                    str(record.snapshot_id),
                ),
            )
        )
