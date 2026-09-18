from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.compare_analysis_snapshots import (
    AnalysisSnapshotNotFoundError,
    CompareAnalysisSnapshots,
    InvalidSnapshotComparisonError,
)
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def make_result(technical, fundamental, stock_quality, entry_quality, price, support, resistance, classification):
    def price_value(value):
        return None if value is None else type("Price", (), {"value": Decimal(value)})()

    def level(value):
        if value is None:
            return None
        return type("Level", (), {"price": type("Price", (), {"value": Decimal(value)})()})()

    return type(
        "Result",
        (),
        {
            "technical_score": type("Score", (), {"total_score": technical})(),
            "fundamental_score": type("Score", (), {"total": fundamental})(),
            "stock_quality": type("Score", (), {"total_score": stock_quality})(),
            "entry_quality": type("Score", (), {"total_score": entry_quality})(),
            "entry_context": type("Context", (), {"current_price": price_value(price), "nearest_support": level(support), "nearest_resistance": level(resistance)})(),
            "opportunity": type("Opportunity", (), {"classification": type("Classification", (), {"value": classification})()})(),
        },
    )()


def build_use_case(stocks):
    store = InMemoryAnalysisResultStore()
    return store, CompareAnalysisSnapshots(InMemoryStockCatalog(stocks), store)


def save_two_snapshots(store, symbol="EGAL"):
    store.save(symbol, make_result(20, 10, 30, 2, "350", "340", "365", "watch"), date(2026, 9, 16))
    store.save(symbol, make_result(25, 12, 35, 4, "360", "345", "370", "buy"), date(2026, 9, 18))
    history = store.get_history(symbol)
    return history[1], history[0]


def test_compares_two_existing_snapshots_and_derives_numeric_deltas():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, use_case = build_use_case([stock])
    before, after = save_two_snapshots(store)
    comparison = use_case.execute("EGAL", before.snapshot_id, after.snapshot_id)
    assert comparison.symbol == "EGAL"
    assert comparison.deltas.technical_score == 5
    assert comparison.deltas.fundamental_score == 2
    assert comparison.deltas.stock_quality == 5
    assert comparison.deltas.entry_quality == 2
    assert comparison.deltas.current_price == Decimal("10")
    assert comparison.deltas.nearest_support == Decimal("5")
    assert comparison.deltas.nearest_resistance == Decimal("5")
    assert comparison.classification_changed is True


def test_caller_selected_direction_is_preserved():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, use_case = build_use_case([stock])
    before, after = save_two_snapshots(store)
    comparison = use_case.execute("EGAL", after.snapshot_id, before.snapshot_id)
    assert comparison.before.snapshot_id == after.snapshot_id
    assert comparison.after.snapshot_id == before.snapshot_id
    assert comparison.deltas.stock_quality == -5


def test_same_date_snapshots_are_distinguished_by_uuid():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, use_case = build_use_case([stock])
    store.save("EGAL", make_result(20, 10, 30, 2, "350", "340", "365", "watch"), date(2026, 9, 18))
    store.save("EGAL", make_result(21, 11, 31, 3, "351", "341", "366", "watch"), date(2026, 9, 18))
    snapshots = store.get_history("EGAL")
    comparison = use_case.execute("EGAL", snapshots[1].snapshot_id, snapshots[0].snapshot_id)
    assert comparison.before.snapshot_id != comparison.after.snapshot_id
    assert comparison.before.analysis_date == comparison.after.analysis_date


def test_identical_snapshot_ids_are_rejected():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, use_case = build_use_case([stock])
    before, _ = save_two_snapshots(store)
    with pytest.raises(InvalidSnapshotComparisonError, match="different"):
        use_case.execute("EGAL", before.snapshot_id, before.snapshot_id)


def test_missing_snapshot_is_rejected():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, use_case = build_use_case([stock])
    with pytest.raises(AnalysisSnapshotNotFoundError):
        use_case.execute("EGAL", uuid4(), uuid4())


def test_cross_symbol_snapshot_is_rejected():
    egal = Stock.create("EGAL", "Egypt Aluminum")
    ieec = Stock.create("IEEC", "Ismailia Engineering")
    store, use_case = build_use_case([egal, ieec])
    before, _ = save_two_snapshots(store, "EGAL")
    store.save("IEEC", make_result(20, 10, 30, 2, "5", "4", "6", "watch"))
    ieec_snapshot = store.get_history("IEEC")[0]
    with pytest.raises(InvalidSnapshotComparisonError, match="EGAL"):
        use_case.execute("EGAL", before.snapshot_id, ieec_snapshot.snapshot_id)


def test_optional_numeric_delta_is_none_when_either_side_is_missing():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, use_case = build_use_case([stock])
    store.save("EGAL", make_result(20, 10, 30, 2, None, None, "365", "watch"), date(2026, 9, 16))
    store.save("EGAL", make_result(21, 11, 31, 3, "351", "341", None, "watch"), date(2026, 9, 18))
    history = store.get_history("EGAL")
    comparison = use_case.execute("EGAL", history[1].snapshot_id, history[0].snapshot_id)
    assert comparison.deltas.current_price is None
    assert comparison.deltas.nearest_support is None
    assert comparison.deltas.nearest_resistance is None


def test_comparison_does_not_execute_analysis():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, use_case = build_use_case([stock])
    before, after = save_two_snapshots(store)
    comparison = use_case.execute("EGAL", before.snapshot_id, after.snapshot_id)
    assert comparison.before.result is before.result
    assert comparison.after.result is after.result