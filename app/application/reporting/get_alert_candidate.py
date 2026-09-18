from app.application.analysis.result_store import AnalysisResultStore
from app.application.stocks.catalog import StockCatalog
from app.domain.reporting.alerts import AlertCandidate, AlertGenerator


class GetAlertCandidate:
    def __init__(self, stock_catalog: StockCatalog, result_store: AnalysisResultStore) -> None:
        self._stock_catalog = stock_catalog
        self._result_store = result_store

    def execute(self, symbol: str) -> AlertCandidate | None:
        stock = self._stock_catalog.get(symbol)
        if stock is None:
            return None

        record = self._result_store.get_record(stock.symbol)
        if record is None:
            return None

        result = record.result
        return AlertGenerator.generate(
            stock_id=stock.id,
            snapshot_id=record.snapshot_id,
            stock_quality=result.stock_quality,
            entry_quality=result.entry_quality,
            classification=result.opportunity.classification,
        )
