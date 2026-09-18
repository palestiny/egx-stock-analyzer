from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.application.analysis.stock_analysis import StockAnalysisResult


@dataclass(frozen=True)
class AnalysisResultRecord:
    result: StockAnalysisResult
    analysis_date: date | None


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


class InMemoryAnalysisResultStore:
    def __init__(self) -> None:
        self._results: dict[str, AnalysisResultRecord] = {}

    def save(
        self,
        symbol: str,
        result: StockAnalysisResult,
        analysis_date: date | None = None,
    ) -> None:
        self._results[symbol] = AnalysisResultRecord(
            result=result,
            analysis_date=analysis_date,
        )

    def get(self, symbol: str) -> StockAnalysisResult | None:
        record = self.get_record(symbol)
        return record.result if record is not None else None

    def get_record(self, symbol: str) -> AnalysisResultRecord | None:
        return self._results.get(symbol)
