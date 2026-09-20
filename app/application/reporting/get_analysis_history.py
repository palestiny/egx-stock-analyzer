from datetime import date

from app.application.analysis.result_store import AnalysisResultRecord, AnalysisResultStore
from app.application.stocks.catalog import StockCatalog
from app.domain.reporting.report import AnalysisReport


class GetAnalysisHistory:
    def __init__(self, stock_catalog: StockCatalog, result_store: AnalysisResultStore) -> None:
        self._stock_catalog = stock_catalog
        self._result_store = result_store

    def execute(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[tuple[AnalysisResultRecord, AnalysisReport], ...] | None:
        stock = self._stock_catalog.get(symbol)
        if stock is None:
            return None

        records = self._result_store.get_history(
            stock.symbol,
            start_date=start_date,
            end_date=end_date,
        )

        reports = []
        for record in records:
            if record.analysis_date is None:
                continue
            result = record.result
            report = AnalysisReport.create(
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
            reports.append((record, report))

        return tuple(reports)
