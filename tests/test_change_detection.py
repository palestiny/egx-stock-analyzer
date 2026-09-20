from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.reporting.change_detection import (
    AnalysisChangeType,
    DetectAnalysisChanges,
)
from app.application.reporting.compare_analysis_snapshots import (
    CompareAnalysisSnapshots,
    InvalidSnapshotComparisonError,
)
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock


def make_result(
    technical,
    fundamental,
    stock_quality,
    entry_quality,
    price,
    support,
    resistance,
    classification,
):
    def price_value(value):
        return None if value is None else type("Price", (), {"value": Decimal(value)})()

    def level(value):
        if value is None:
            return None
        return type(
            "Level",
            (),
            {"price": type("Price", (), {"value": Decimal(value)})()},
        )()

    return type(
        "Result",
        (),
        {
            "technical_score": type("Score", (), {"total_score": technical})(),
            "fundamental_score": type("Score", (), {"total": fundamental})(),
            "stock_quality": type("Score", (), {"total_score": stock_quality})(),
            "entry_quality": type("Score", (), {"total_score": entry_quality})(),
            "entry_context": type(
                "Context",
                (),
                {
                    "current_price": price_value(price),
                    "nearest_support": level(support),
                    "nearest_resistance": level(resistance),
                },
            )(),
            "opportunity": type(
                "Opportunity",
                (),
                {"classification": type("Classification", (), {"value": classification})()},
            )(),
        },
    )()


def build_use_case(stocks):
    store = InMemoryAnalysisResultStore()
    comparison = CompareAnalysisSnapshots(InMemoryStockCatalog(stocks), store)
    return store, DetectAnalysisChanges(comparison)


def save_two_snapshots(store, symbol="EGAL"):
    store.save(
        symbol,
        make_result(20, 10, 30, 2, "350", "340", "365", "watch"),
        date(2026, 9, 16),
    )
    store.save(
        symbol,
        make_result(25, 12, 35, 4, "360", "345", "370", "buy"),
        date(2026, 9, 18),
    )
    history = store.get_history(symbol)
    return history[1], history[0]


def test_detects_changed_analytical_dimensions_in_deterministic_order():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, detector = build_use_case([stock])
    before, after = save_two_snapshots(store)

    result = detector.execute("EGAL", before.snapshot_id, after.snapshot_id)

    assert result.changes == (
        AnalysisChangeType.CLASSIFICATION,
        AnalysisChangeType.TECHNICAL_SCORE,
        AnalysisChangeType.FUNDAMENTAL_SCORE,
        AnalysisChangeType.STOCK_QUALITY,
        AnalysisChangeType.ENTRY_QUALITY,
        AnalysisChangeType.CURRENT_PRICE,
        AnalysisChangeType.NEAREST_SUPPORT,
        AnalysisChangeType.NEAREST_RESISTANCE,
    )


def test_unchanged_dimensions_are_not_reported():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, detector = build_use_case([stock])
    store.save("EGAL", make_result(20, 10, 30, 2, "350", "340", "365", "watch"))
    store.save("EGAL", make_result(20, 10, 30, 2, "350", "340", "365", "watch"))
    snapshots = store.get_history("EGAL")

    result = detector.execute("EGAL", snapshots[1].snapshot_id, snapshots[0].snapshot_id)

    assert result.changes == ()


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        (None, "350", True),
        ("350", None, True),
        (None, None, False),
        ("350", "350", False),
        ("350", "351", True),
    ],
)
def test_optional_price_change_detection(before, after, expected):
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, detector = build_use_case([stock])
    store.save("EGAL", make_result(20, 10, 30, 2, before, "340", "365", "watch"))
    store.save("EGAL", make_result(20, 10, 30, 2, after, "340", "365", "watch"))
    snapshots = store.get_history("EGAL")

    result = detector.execute("EGAL", snapshots[1].snapshot_id, snapshots[0].snapshot_id)

    assert (AnalysisChangeType.CURRENT_PRICE in result.changes) is expected


def test_optional_support_and_resistance_availability_changes_are_detected():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, detector = build_use_case([stock])
    store.save("EGAL", make_result(20, 10, 30, 2, "350", None, "365", "watch"))
    store.save("EGAL", make_result(20, 10, 30, 2, "350", "340", None, "watch"))
    snapshots = store.get_history("EGAL")

    result = detector.execute("EGAL", snapshots[1].snapshot_id, snapshots[0].snapshot_id)

    assert result.changes == (
        AnalysisChangeType.NEAREST_SUPPORT,
        AnalysisChangeType.NEAREST_RESISTANCE,
    )


def test_detector_reuses_comparison_validation():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, detector = build_use_case([stock])
    before, _ = save_two_snapshots(store)

    with pytest.raises(InvalidSnapshotComparisonError, match="different"):
        detector.execute("EGAL", before.snapshot_id, before.snapshot_id)


def test_detector_returns_original_comparison_read_model():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    store, detector = build_use_case([stock])
    before, after = save_two_snapshots(store)

    result = detector.execute("EGAL", before.snapshot_id, after.snapshot_id)

    assert result.comparison.before.snapshot_id == before.snapshot_id
    assert result.comparison.after.snapshot_id == after.snapshot_id


def test_change_type_order_is_stable():
    assert tuple(AnalysisChangeType) == (
        AnalysisChangeType.CLASSIFICATION,
        AnalysisChangeType.TECHNICAL_SCORE,
        AnalysisChangeType.FUNDAMENTAL_SCORE,
        AnalysisChangeType.STOCK_QUALITY,
        AnalysisChangeType.ENTRY_QUALITY,
        AnalysisChangeType.CURRENT_PRICE,
        AnalysisChangeType.NEAREST_SUPPORT,
        AnalysisChangeType.NEAREST_RESISTANCE,
    )


def test_missing_snapshots_are_rejected():
    stock = Stock.create("EGAL", "Egypt Aluminum")
    _, detector = build_use_case([stock])

    with pytest.raises(ValueError):
        detector.execute("EGAL", uuid4(), uuid4())
