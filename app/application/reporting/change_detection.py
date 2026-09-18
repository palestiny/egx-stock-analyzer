from dataclasses import dataclass
from enum import Enum

from app.application.reporting.compare_analysis_snapshots import (
    AnalysisSnapshotComparison,
    CompareAnalysisSnapshots,
)
class AnalysisChangeType(Enum):
    CLASSIFICATION = "classification"
    TECHNICAL_SCORE = "technical_score"
    FUNDAMENTAL_SCORE = "fundamental_score"
    STOCK_QUALITY = "stock_quality"
    ENTRY_QUALITY = "entry_quality"
    CURRENT_PRICE = "current_price"
    NEAREST_SUPPORT = "nearest_support"
    NEAREST_RESISTANCE = "nearest_resistance"


@dataclass(frozen=True)
class AnalysisChangeDetection:
    symbol: str
    comparison: AnalysisSnapshotComparison
    changes: tuple[AnalysisChangeType, ...]


class DetectAnalysisChanges:
    def __init__(self, compare_analysis_snapshots: CompareAnalysisSnapshots) -> None:
        self._compare_analysis_snapshots = compare_analysis_snapshots

    def execute(
        self,
        symbol: str,
        before_snapshot_id,
        after_snapshot_id,
    ) -> AnalysisChangeDetection:
        comparison = self._compare_analysis_snapshots.execute(
            symbol,
            before_snapshot_id,
            after_snapshot_id,
        )

        before = comparison.before.result
        after = comparison.after.result
        changes: list[AnalysisChangeType] = []

        if before.opportunity.classification.value != after.opportunity.classification.value:
            changes.append(AnalysisChangeType.CLASSIFICATION)

        if before.technical_score.total_score != after.technical_score.total_score:
            changes.append(AnalysisChangeType.TECHNICAL_SCORE)

        if before.fundamental_score.total != after.fundamental_score.total:
            changes.append(AnalysisChangeType.FUNDAMENTAL_SCORE)

        if before.stock_quality.total_score != after.stock_quality.total_score:
            changes.append(AnalysisChangeType.STOCK_QUALITY)

        if before.entry_quality.total_score != after.entry_quality.total_score:
            changes.append(AnalysisChangeType.ENTRY_QUALITY)

        if _optional_price_changed(
            before.entry_context.current_price,
            after.entry_context.current_price,
        ):
            changes.append(AnalysisChangeType.CURRENT_PRICE)

        if _optional_level_changed(
            before.entry_context.nearest_support,
            after.entry_context.nearest_support,
        ):
            changes.append(AnalysisChangeType.NEAREST_SUPPORT)

        if _optional_level_changed(
            before.entry_context.nearest_resistance,
            after.entry_context.nearest_resistance,
        ):
            changes.append(AnalysisChangeType.NEAREST_RESISTANCE)

        return AnalysisChangeDetection(
            symbol=comparison.symbol,
            comparison=comparison,
            changes=tuple(changes),
        )


def _optional_price_changed(before, after) -> bool:
    if before is None or after is None:
        return before is not after
    return before.value != after.value


def _optional_level_changed(before, after) -> bool:
    if before is None or after is None:
        return before is not after
    return before.price.value != after.price.value
