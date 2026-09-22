from app.domain.fundamental_analysis.historical_financial_snapshot import HistoricalFinancialSnapshot
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.stocks.stock import Stock
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader


class HistoricalDatasetFundamentalSnapshotSource:
    """Adapts dataset financial records to the point-in-time snapshot boundary."""

    def __init__(self, loader: HistoricalDatasetLoader) -> None:
        self._loader = loader

    def get_snapshots(self, stock: Stock) -> list[HistoricalFinancialSnapshot]:
        records = self._loader.load_financial_snapshots()
        return [
            HistoricalFinancialSnapshot(
                period=FinancialPeriod(
                    period_end=record.period_end,
                    revenue=record.revenue,
                    net_income=record.net_income,
                    current_assets=record.current_assets,
                    current_liabilities=record.current_liabilities,
                ),
                available_at=record.available_at,
            )
            for record in records
            if record.stock_id == stock.id
        ]
