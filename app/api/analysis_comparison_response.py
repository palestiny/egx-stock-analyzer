from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from app.application.reporting.compare_analysis_snapshots import (
    AnalysisSnapshotComparison,
)
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.domain.reporting.report import AnalysisReport


@dataclass(frozen=True)
class AnalysisComparisonSnapshotResponse:
    snapshot_id: str
    analysis_date: object | None
    technical_score: int
    fundamental_score: int
    stock_quality: int
    entry_quality: int
    opportunity: str
    current_price: float | None
    nearest_support: float | None
    nearest_resistance: float | None

    @classmethod
    def from_record(cls, record) -> "AnalysisComparisonSnapshotResponse":
        result = record.result
        return cls(
            snapshot_id=str(record.snapshot_id),
            analysis_date=record.analysis_date,
            technical_score=result.technical_score.total_score,
            fundamental_score=result.fundamental_score.total,
            stock_quality=result.stock_quality.total_score,
            entry_quality=result.entry_quality.total_score,
            opportunity=result.opportunity.classification.value,
            current_price=cls._float_value(result.entry_context.current_price),
            nearest_support=cls._float_value(
                result.entry_context.nearest_support,
                nested_price=True,
            ),
            nearest_resistance=cls._float_value(
                result.entry_context.nearest_resistance,
                nested_price=True,
            ),
        )

    @staticmethod
    def _float_value(value, nested_price: bool = False) -> float | None:
        if value is None:
            return None
        decimal_value = value.price.value if nested_price else value.value
        return float(decimal_value)


@dataclass(frozen=True)
class AnalysisComparisonDeltasResponse:
    technical_score: int
    fundamental_score: int
    stock_quality: int
    entry_quality: int
    current_price: float | None
    nearest_support: float | None
    nearest_resistance: float | None

    @classmethod
    def from_deltas(cls, deltas) -> "AnalysisComparisonDeltasResponse":
        return cls(
            technical_score=deltas.technical_score,
            fundamental_score=deltas.fundamental_score,
            stock_quality=deltas.stock_quality,
            entry_quality=deltas.entry_quality,
            current_price=cls._float_decimal(deltas.current_price),
            nearest_support=cls._float_decimal(deltas.nearest_support),
            nearest_resistance=cls._float_decimal(deltas.nearest_resistance),
        )

    @staticmethod
    def _float_decimal(value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


@dataclass(frozen=True)
class AnalysisComparisonResponse:
    symbol: str
    before: AnalysisComparisonSnapshotResponse
    after: AnalysisComparisonSnapshotResponse
    deltas: AnalysisComparisonDeltasResponse
    classification_changed: bool

    @classmethod
    def from_comparison(
        cls,
        comparison: AnalysisSnapshotComparison,
    ) -> "AnalysisComparisonResponse":
        return cls(
            symbol=comparison.symbol,
            before=AnalysisComparisonSnapshotResponse.from_record(comparison.before),
            after=AnalysisComparisonSnapshotResponse.from_record(comparison.after),
            deltas=AnalysisComparisonDeltasResponse.from_deltas(comparison.deltas),
            classification_changed=comparison.classification_changed,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
