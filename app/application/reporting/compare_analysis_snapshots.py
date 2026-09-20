from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.application.analysis.result_store import AnalysisResultRecord, AnalysisResultStore
from app.application.stocks.catalog import StockCatalog


class AnalysisSnapshotNotFoundError(ValueError):
    """Raised when a requested historical analysis snapshot does not exist."""


class InvalidSnapshotComparisonError(ValueError):
    """Raised when selected snapshots cannot be compared for the requested stock."""


@dataclass(frozen=True)
class AnalysisSnapshotComparisonDeltas:
    technical_score: int
    fundamental_score: int
    stock_quality: int
    entry_quality: int
    current_price: Decimal | None
    nearest_support: Decimal | None
    nearest_resistance: Decimal | None


@dataclass(frozen=True)
class AnalysisSnapshotComparison:
    symbol: str
    before: AnalysisResultRecord
    after: AnalysisResultRecord
    deltas: AnalysisSnapshotComparisonDeltas
    classification_changed: bool


class CompareAnalysisSnapshots:
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
    ) -> AnalysisSnapshotComparison:
        stock = self._stock_catalog.get(symbol)
        if stock is None:
            raise AnalysisSnapshotNotFoundError(
                f"Analysis snapshot not found for {symbol}"
            )

        if before_snapshot_id == after_snapshot_id:
            raise InvalidSnapshotComparisonError(
                "Before and after snapshots must be different"
            )

        before = self._result_store.get_snapshot(before_snapshot_id)
        after = self._result_store.get_snapshot(after_snapshot_id)

        if before is None or after is None:
            raise AnalysisSnapshotNotFoundError("Requested analysis snapshot not found")

        requested_symbol = stock.symbol
        if before.symbol != requested_symbol or after.symbol != requested_symbol:
            raise InvalidSnapshotComparisonError(
                f"Snapshots must belong to {requested_symbol}"
            )

        return AnalysisSnapshotComparison(
            symbol=requested_symbol,
            before=before,
            after=after,
            deltas=AnalysisSnapshotComparisonDeltas(
                technical_score=(
                    after.result.technical_score.total_score
                    - before.result.technical_score.total_score
                ),
                fundamental_score=(
                    after.result.fundamental_score.total
                    - before.result.fundamental_score.total
                ),
                stock_quality=(
                    after.result.stock_quality.total_score
                    - before.result.stock_quality.total_score
                ),
                entry_quality=(
                    after.result.entry_quality.total_score
                    - before.result.entry_quality.total_score
                ),
                current_price=self._decimal_delta(
                    before.result.entry_context.current_price,
                    after.result.entry_context.current_price,
                ),
                nearest_support=self._decimal_delta(
                    before.result.entry_context.nearest_support,
                    after.result.entry_context.nearest_support,
                    nested_price=True,
                ),
                nearest_resistance=self._decimal_delta(
                    before.result.entry_context.nearest_resistance,
                    after.result.entry_context.nearest_resistance,
                    nested_price=True,
                ),
            ),
            classification_changed=(
                before.result.opportunity.classification
                != after.result.opportunity.classification
            ),
        )

    @staticmethod
    def _decimal_delta(before, after, nested_price: bool = False) -> Decimal | None:
        if before is None or after is None:
            return None

        before_value = before.price.value if nested_price else before.value
        after_value = after.price.value if nested_price else after.value
        return after_value - before_value
