from app.application.analysis.result_store import AnalysisResultStore
from app.application.stocks.catalog import StockCatalog
from app.domain.reporting.report import AnalysisReport


class GetAnalysisReport:
    def __init__(self, stock_catalog: StockCatalog, result_store: AnalysisResultStore) -> None:
        self._stock_catalog = stock_catalog
        self._result_store = result_store

    def execute(self, symbol: str) -> AnalysisReport | None:
        stock = self._stock_catalog.get(symbol)
        if stock is None:
            return None

        record = self._result_store.get_record(stock.symbol)
        if record is None or record.analysis_date is None:
            return None

        result = record.result
        return AnalysisReport.create(
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            analysis_date=record.analysis_date,
            technical_analysis=result.technical_analysis,
            fundamental_analysis=result.fundamental_analysis,
            stock_quality=result.stock_quality,
            entry_context=result.entry_context,
            entry_quality=result.entry_quality,
            classification=result.opportunity,
        )
