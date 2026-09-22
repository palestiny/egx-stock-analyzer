from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class HistoricalMarketObservation:
    stock_id: UUID
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source: str


@dataclass(frozen=True)
class HistoricalFinancialSnapshotRecord:
    stock_id: UUID
    period_end: date
    available_at: date
    revenue: Decimal
    net_income: Decimal
    current_assets: Decimal | None
    current_liabilities: Decimal | None
    source: str
    revision: str


@dataclass(frozen=True)
class DatasetCoverage:
    start: str
    end: str
    stock_count: int


@dataclass(frozen=True)
class DatasetArtifact:
    path: Path
    sha256: str
    row_count: int
    coverage: DatasetCoverage


@dataclass(frozen=True)
class HistoricalDatasetManifest:
    dataset_id: str
    dataset_version: str
    schema_version: str
    market_observations: DatasetArtifact
    financial_snapshots: DatasetArtifact
