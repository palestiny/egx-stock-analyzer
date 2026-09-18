from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.analysis.result_store import AnalysisResultRecord, InMemoryAnalysisResultStore
from app.application.reporting.calculate_snapshot_performance import (
    CalculateSnapshotPerformance,
    AnalysisSnapshotPerformanceNotFoundError,
    InvalidSnapshotPerformanceError,
)
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.market_data.price import Price
from app.domain.stocks.stock import Stock


def record(symbol: str, price: str, analysis_date: date) -> AnalysisResultRecord:
    result = SimpleNamespace(
        entry_context=SimpleNamespace(current_price=Price(Decimal(price)))
    )
    return AnalysisResultRecord(
        result=result,
        analysis_date=analysis_date,
        snapshot_id=uuid4(),
        symbol=symbol,
    )


class SnapshotStore(InMemoryAnalysisResultStore):
    def save_record(self, record: AnalysisResultRecord) -> None:
        self._results.setdefault(record.symbol, []).append(record)


def setup():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    catalog = InMemoryStockCatalog([stock])
    store = SnapshotStore()
    return catalog, store


def test_calculates_absolute_and_percentage_price_change():
    catalog, store = setup()
    before = record("EGAL", "100", date(2026, 9, 1))
    after = record("EGAL", "125", date(2026, 9, 10))
    store.save_record(before)
    store.save_record(after)

    result = CalculateSnapshotPerformance(catalog, store).execute(
        "egal", before.snapshot_id, after.snapshot_id
    )

    assert result.symbol == "EGAL"
    assert result.metrics.price_change == Decimal("25")
    assert result.metrics.price_change_percent == Decimal("25")


def test_preserves_caller_selected_direction():
    catalog, store = setup()
    before = record("EGAL", "125", date(2026, 9, 10))
    after = record("EGAL", "100", date(2026, 9, 1))
    store.save_record(before)
    store.save_record(after)

    result = CalculateSnapshotPerformance(catalog, store).execute(
        "EGAL", before.snapshot_id, after.snapshot_id
    )

    assert result.metrics.price_change == Decimal("-25")
    assert result.metrics.price_change_percent == Decimal("-20")


def test_missing_price_makes_metrics_unavailable():
    catalog, store = setup()
    before = record("EGAL", "100", date(2026, 9, 1))
    after = AnalysisResultRecord(
        result=SimpleNamespace(entry_context=SimpleNamespace(current_price=None)),
        analysis_date=date(2026, 9, 10),
        snapshot_id=uuid4(),
        symbol="EGAL",
    )
    store.save_record(before)
    store.save_record(after)

    result = CalculateSnapshotPerformance(catalog, store).execute(
        "EGAL", before.snapshot_id, after.snapshot_id
    )

    assert result.metrics.price_change is None
    assert result.metrics.price_change_percent is None


def test_zero_before_price_keeps_absolute_change_and_marks_percentage_unavailable():
    catalog, store = setup()
    before = record("EGAL", "0", date(2026, 9, 1))
    after = record("EGAL", "10", date(2026, 9, 10))
    store.save_record(before)
    store.save_record(after)

    result = CalculateSnapshotPerformance(catalog, store).execute(
        "EGAL", before.snapshot_id, after.snapshot_id
    )

    assert result.metrics.price_change == Decimal("10")
    assert result.metrics.price_change_percent is None


def test_missing_snapshot_is_explicit():
    catalog, store = setup()

    with pytest.raises(AnalysisSnapshotPerformanceNotFoundError):
        CalculateSnapshotPerformance(catalog, store).execute(
            "EGAL", uuid4(), uuid4()
        )


def test_cross_symbol_snapshots_are_rejected():
    catalog, store = setup()
    before = record("EGAL", "100", date(2026, 9, 1))
    after = record("COMI", "125", date(2026, 9, 10))
    store.save_record(before)
    store.save_record(after)

    with pytest.raises(InvalidSnapshotPerformanceError):
        CalculateSnapshotPerformance(catalog, store).execute(
            "EGAL", before.snapshot_id, after.snapshot_id
        )


def test_identical_snapshot_ids_are_rejected():
    catalog, store = setup()
    before = record("EGAL", "100", date(2026, 9, 1))
    store.save_record(before)

    with pytest.raises(InvalidSnapshotPerformanceError):
        CalculateSnapshotPerformance(catalog, store).execute(
            "EGAL", before.snapshot_id, before.snapshot_id
        )
