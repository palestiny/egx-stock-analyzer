from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.fundamental_data.historical_provider import (
    PointInTimeFundamentalDataProvider,
)
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.historical_financial_snapshot import (
    HistoricalFinancialSnapshot,
)
from app.domain.stocks.stock import Stock


def period(year: int, revenue: str) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=date(year, 12, 31),
        revenue=Decimal(revenue),
        net_income=Decimal("10"),
    )


def snapshot(
    year: int,
    available: date,
    revenue: str = "100",
) -> HistoricalFinancialSnapshot:
    return HistoricalFinancialSnapshot(
        period=period(year, revenue),
        available_at=available,
    )


def test_only_snapshots_available_at_decision_date_are_visible():
    stock = Stock(uuid4(), "EGAL", "Egypt Aluminium")
    source = _Source(
        [
            snapshot(2024, date(2025, 2, 15), "2024"),
            snapshot(2023, date(2024, 2, 15), "2023"),
            snapshot(2025, date(2026, 2, 15), "2025"),
        ]
    )

    current, previous = PointInTimeFundamentalDataProvider(source).get_periods(
        stock,
        date(2025, 3, 1),
    )

    assert current.period_end == date(2024, 12, 31)
    assert previous.period_end == date(2023, 12, 31)


def test_latest_available_revision_is_selected_for_same_period_end():
    stock = Stock(uuid4(), "EGAL", "Egypt Aluminium")
    source = _Source(
        [
            snapshot(2024, date(2025, 2, 15), "100"),
            snapshot(2024, date(2025, 5, 15), "120"),
            snapshot(2023, date(2024, 2, 15), "90"),
        ]
    )

    current, _ = PointInTimeFundamentalDataProvider(source).get_periods(
        stock,
        date(2025, 6, 1),
    )

    assert current.period_end == date(2024, 12, 31)
    assert current.revenue == Decimal("120")


def test_future_snapshot_cannot_be_used_even_when_period_end_is_eligible():
    stock = Stock(uuid4(), "EGAL", "Egypt Aluminium")
    source = _Source(
        [
            snapshot(2025, date(2026, 2, 15)),
            snapshot(2024, date(2025, 2, 15)),
            snapshot(2023, date(2024, 2, 15)),
        ]
    )

    current, previous = PointInTimeFundamentalDataProvider(source).get_periods(
        stock,
        date(2025, 12, 1),
    )

    assert current.period_end == date(2024, 12, 31)
    assert previous.period_end == date(2023, 12, 31)


def test_missing_point_in_time_history_fails_explicitly():
    stock = Stock(uuid4(), "EGAL", "Egypt Aluminium")
    source = _Source([snapshot(2024, date(2025, 2, 15))])

    with pytest.raises(ValueError, match="Insufficient point-in-time"):
        PointInTimeFundamentalDataProvider(source).get_periods(
            stock,
            date(2025, 3, 1),
        )


def test_availability_before_period_end_is_rejected():
    with pytest.raises(ValueError, match="available_at"):
        snapshot(2024, date(2024, 12, 30))


class _Source:
    def __init__(self, snapshots):
        self._snapshots = snapshots

    def get_snapshots(self, stock):
        return list(self._snapshots)
