from dataclasses import dataclass, field
from datetime import date
from typing import Protocol
from uuid import UUID, uuid4

from app.application.analysis.stock_analysis import StockAnalysisResult


@dataclass(frozen=True)
class AnalysisResultRecord:
    result: StockAnalysisResult
    analysis_date: date | None
    snapshot_id: UUID = field(default_factory=uuid4)


class AnalysisResultStore(Protocol):
    def save(
        self,
        symbol: str,
        result: StockAnalysisResult,
        analysis_date: date | None = None,
    ) -> None:
        ...

    def get(self, symbol: str) -> StockAnalysisResult | None:
        ...

    def get_record(self, symbol: str) -> AnalysisResultRecord | None:
        ...

    def get_history(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[AnalysisResultRecord, ...]:
        ...


class InMemoryAnalysisResultStore:
    def __init__(self) -> None:
        self._results: dict[str, list[AnalysisResultRecord]] = {}

    def save(
        self,
        symbol: str,
        result: StockAnalysisResult,
        analysis_date: date | None = None,
    ) -> None:
        records = self._results.setdefault(symbol, [])
        records.append(
            AnalysisResultRecord(
                result=result,
                analysis_date=analysis_date,
            )
        )

    def get(self, symbol: str) -> StockAnalysisResult | None:
        record = self.get_record(symbol)
        return record.result if record is not None else None

    def get_record(self, symbol: str) -> AnalysisResultRecord | None:
        history = self.get_history(symbol)
        return history[0] if history else None

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
