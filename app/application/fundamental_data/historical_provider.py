from datetime import date
from typing import Protocol

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.historical_financial_snapshot import (
    HistoricalFinancialSnapshot,
)
from app.domain.stocks.stock import Stock


class HistoricalFundamentalSnapshotSource(Protocol):
    def get_snapshots(
        self,
        stock: Stock,
    ) -> list[HistoricalFinancialSnapshot]:
        ...


class PointInTimeFundamentalDataProvider:
    """Selects only financial snapshots proven available at a decision date."""

    def __init__(self, source: HistoricalFundamentalSnapshotSource) -> None:
        self._source = source

    def get_periods(
        self,
        stock: Stock,
        as_of: date,
    ) -> tuple[FinancialPeriod, FinancialPeriod]:
        available = [
            snapshot
            for snapshot in self._source.get_snapshots(stock)
            if snapshot.is_available_at(as_of)
        ]

        latest_by_period_end: dict[date, HistoricalFinancialSnapshot] = {}
        for snapshot in available:
            period_end = snapshot.period.period_end
            current = latest_by_period_end.get(period_end)
            if current is None or snapshot.available_at > current.available_at:
                latest_by_period_end[period_end] = snapshot

        ordered = sorted(
            latest_by_period_end.values(),
            key=lambda snapshot: snapshot.period.period_end,
            reverse=True,
        )

        if len(ordered) < 2:
            raise ValueError(
                "Insufficient point-in-time financial snapshots available for analysis"
            )

        return (
            ordered[0].to_financial_period(),
            ordered[1].to_financial_period(),
        )
