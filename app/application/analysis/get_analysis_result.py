from app.application.analysis.result_store import AnalysisResultStore
from app.application.analysis.stock_analysis import StockAnalysisResult


class GetAnalysisResult:
    def __init__(self, result_store: AnalysisResultStore) -> None:
        self._result_store = result_store

    def execute(self, symbol: str) -> StockAnalysisResult | None:
        return self._result_store.get(symbol)
