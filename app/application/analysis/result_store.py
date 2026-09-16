from typing import Protocol

from app.application.analysis.stock_analysis import StockAnalysisResult


class AnalysisResultStore(Protocol):
    def save(self, symbol: str, result: StockAnalysisResult) -> None:
        ...

    def get(self, symbol: str) -> StockAnalysisResult | None:
        ...


class InMemoryAnalysisResultStore:
    def __init__(self) -> None:
        self._results: dict[str, StockAnalysisResult] = {}

    def save(self, symbol: str, result: StockAnalysisResult) -> None:
        self._results[symbol] = result

    def get(self, symbol: str) -> StockAnalysisResult | None:
        return self._results.get(symbol)
