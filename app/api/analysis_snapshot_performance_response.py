from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from app.application.reporting.calculate_snapshot_performance import AnalysisSnapshotPerformance

@dataclass(frozen=True)
class AnalysisSnapshotPerformanceSnapshotResponse:
    snapshot_id: str
    analysis_date: date | None
    current_price: float | None

    @classmethod
    def from_record(cls, record):
        current_price = record.result.entry_context.current_price
        return cls(
            snapshot_id=str(record.snapshot_id),
            analysis_date=record.analysis_date,
            current_price=float(current_price.value) if current_price is not None else None,
        )

@dataclass(frozen=True)
class SnapshotPerformanceMetricsResponse:
    price_change: float | None
    price_change_percent: float | None

    @classmethod
    def from_metrics(cls, metrics):
        return cls(
            price_change=float(metrics.price_change) if metrics.price_change is not None else None,
            price_change_percent=float(metrics.price_change_percent) if metrics.price_change_percent is not None else None,
        )

@dataclass(frozen=True)
class AnalysisSnapshotPerformanceResponse:
    symbol: str
    before: AnalysisSnapshotPerformanceSnapshotResponse
    after: AnalysisSnapshotPerformanceSnapshotResponse
    metrics: SnapshotPerformanceMetricsResponse

    @classmethod
    def from_performance(cls, performance: AnalysisSnapshotPerformance):
        return cls(
            symbol=performance.symbol,
            before=AnalysisSnapshotPerformanceSnapshotResponse.from_record(performance.before),
            after=AnalysisSnapshotPerformanceSnapshotResponse.from_record(performance.after),
            metrics=SnapshotPerformanceMetricsResponse.from_metrics(performance.metrics),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
