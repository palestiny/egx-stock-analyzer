from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID

from .generator import MarketRegime, SyntheticDataset


class SyntheticEventType(Enum):
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    VOLUME_SPIKE = "volume_spike"
    GAP = "gap"
    SUSPENSION = "suspension"
    CORPORATE_ACTION = "corporate_action"
    EARNINGS_RELEASE = "earnings_release"
    MARKET_CRASH = "market_crash"


@dataclass(frozen=True)
class SyntheticFinancialSnapshot:
    stock_id: UUID
    period_end: date
    available_at: datetime
    revenue: Decimal
    net_income: Decimal
    current_assets: Decimal
    current_liabilities: Decimal
    source: str
    revision: str

    def __post_init__(self) -> None:
        if self.available_at.tzinfo is None or self.available_at.utcoffset() is None:
            raise ValueError("available_at must be timezone-aware")
        if self.available_at.date() < self.period_end:
            raise ValueError("financial data cannot be available before period end")
        if not self.source or not self.revision:
            raise ValueError("source and revision are required")


@dataclass(frozen=True)
class SyntheticMarketEvent:
    symbol: str
    timestamp: datetime
    event_type: SyntheticEventType
    magnitude: Decimal
    description: str


@dataclass(frozen=True)
class SyntheticRelationship:
    left_symbol: str
    right_symbol: str
    relationship: str
    coefficient: Decimal


@dataclass(frozen=True)
class SyntheticResearchScenario:
    dataset: SyntheticDataset
    financial_snapshots: tuple[SyntheticFinancialSnapshot, ...]
    events: tuple[SyntheticMarketEvent, ...]
    relationships: tuple[SyntheticRelationship, ...]


class SyntheticResearchScenarioBuilder:
    def build(self, dataset: SyntheticDataset) -> SyntheticResearchScenario:
        financial: list[SyntheticFinancialSnapshot] = []
        events: list[SyntheticMarketEvent] = []
        relationships: list[SyntheticRelationship] = []

        for series in dataset.series:
            stock_id = series.stock_id
            for year in range(2021, 2026):
                period_end = date(year, 12, 31)
                financial.append(
                    SyntheticFinancialSnapshot(
                        stock_id=stock_id,
                        period_end=period_end,
                        available_at=datetime(year + 1, 3, 31, tzinfo=timezone.utc),
                        revenue=Decimal("1000000") * Decimal(str(1 + 0.06 * (year - 2020))),
                        net_income=Decimal("120000") * Decimal(str(1 + 0.04 * (year - 2020))),
                        current_assets=Decimal("900000"),
                        current_liabilities=Decimal("600000"),
                        source="synthetic-fixture",
                        revision=f"v{year}",
                    )
                )

            for index in (180, 360, 560, 760):
                if index < len(series.bars):
                    bar = series.bars[index]
                    event_type = (
                        SyntheticEventType.MARKET_CRASH
                        if series.regimes[index] is MarketRegime.CRASH
                        else SyntheticEventType.VOLUME_SPIKE
                    )
                    events.append(
                        SyntheticMarketEvent(
                            symbol=series.symbol,
                            timestamp=bar.timestamp,
                            event_type=event_type,
                            magnitude=Decimal("4"),
                            description="Controlled synthetic research event",
                        )
                    )

        symbols = [series.symbol for series in dataset.series]
        for index in range(0, len(symbols) - 1, 2):
            relationships.append(
                SyntheticRelationship(
                    left_symbol=symbols[index],
                    right_symbol=symbols[index + 1],
                    relationship="sector_peer",
                    coefficient=Decimal("0.65"),
                )
            )

        return SyntheticResearchScenario(
            dataset=dataset,
            financial_snapshots=tuple(financial),
            events=tuple(events),
            relationships=tuple(relationships),
        )
