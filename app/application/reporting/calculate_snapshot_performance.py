from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.application.analysis.result_store import AnalysisResultRecord, AnalysisResultStore
from app.application.stocks.catalog import StockCatalog


class AnalysisSnapshotPerformanceNotFoundError(ValueError):
    """Raised when a requested historical analysis snapshot does not exist."""


class InvalidSnapshotPerformanceError(ValueError):
    """Raised when selected snapshots cannot be used for performance measurement."""


@dataclass(frozen=True)
class SnapshotPerformanceMetrics:
    price_change: Decimal | None
    price_change_percent: Decimal | None


@dataclass(frozen=True)
class AnalysisSnapshotPerformance:
    symbol: str
    before: AnalysisResultRecord
    after: AnalysisResultRecord
    metrics: SnapshotPerformanceMetrics


class CalculateSnapshotPerformance:
    def __init__(
        self,
        stock_catalog: StockCatalog,
        result_store: AnalysisResultStore,
    ) -> None:
        self._stock_catalog = stock_catalog
        self._result_store = result_store

    def execute(
        self,
        symbol: str,
        before_snapshot_id: UUID,
        after_snapshot_id: UUID,
    ) -> AnalysisSnapshotPerformance:
        stock = self._stock_catalog.get(symbol)
        if stock is None:
            raise AnalysisSnapshotPerformanceNotFoundError(
                f"Analysis snapshot not found for {symbol}"
            )

        if before_snapshot_id == after_snapshot_id:
            raise InvalidSnapshotPerformanceError(
                "Before and after snapshots must be different"
            )

        before = self._result_store.get_snapshot(before_snapshot_id)
        after = self._result_store.get_snapshot(after_snapshot_id)

        if before is None or after is None:
            raise AnalysisSnapshotPerformanceNotFoundError(
                "Requested analysis snapshot not found"
            )

        requested_symbol = stock.symbol
        if before.symbol != requested_symbol or after.symbol != requested_symbol:
            raise InvalidSnapshotPerformanceError(
                f"Snapshots must belong to {requested_symbol}"
            )

        before_price = self._current_price(before)
        after_price = self._current_price(after)

        price_change = None
        price_change_percent = None

        if before_price is not None and after_price is not None:
            price_change = after_price - before_price
            if before_price != Decimal("0"):
                price_change_percent = (price_change / before_price) * Decimal("100")

        return AnalysisSnapshotPerformance(
            symbol=requested_symbol,
            before=before,
            after=after,
            metrics=SnapshotPerformanceMetrics(
                price_change=price_change,
                price_change_percent=price_change_percent,
            ),
        )

    @staticmethod
    def _current_price(record: AnalysisResultRecord) -> Decimal | None:
        current_price = record.result.entry_context.current_price
        return current_price.value if current_price is not None else None
