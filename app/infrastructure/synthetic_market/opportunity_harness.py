from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entry_analysis.context import EntryContextAnalyzer
from app.domain.entry_analysis.scoring import EntryQualityScore, EntryQualityScorer
from app.domain.opportunity.classification import (
    OpportunityClassification,
    OpportunityClassifier,
)
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.technical_analysis.support_resistance import SupportResistanceAnalyzer
from app.domain.market_data.timeframe import Timeframe

from .generator import SyntheticDataset
from .feature_harness import SyntheticFeatureReport
from .quality_harness import SyntheticQualityReport


@dataclass(frozen=True)
class SyntheticOpportunitySnapshot:
    symbol: str
    stock_id: UUID
    stock_quality_score: int
    entry_quality_score: EntryQualityScore
    classification: OpportunityClassification


@dataclass(frozen=True)
class SyntheticOpportunityReport:
    scenario_name: str
    seed: int
    snapshots: tuple[SyntheticOpportunitySnapshot, ...]

    @property
    def counts(self) -> dict[OpportunityClassification, int]:
        return {
            classification: sum(
                snapshot.classification is classification
                for snapshot in self.snapshots
            )
            for classification in OpportunityClassification
        }


class SyntheticOpportunityHarness:
    """Composes existing quality and entry domains into opportunity decisions."""

    def run(
        self,
        dataset: SyntheticDataset,
        features: SyntheticFeatureReport,
        quality: SyntheticQualityReport,
    ) -> SyntheticOpportunityReport:
        feature_by_stock = {item.stock_id: item for item in features.snapshots}
        quality_by_stock = {item.stock_id: item for item in quality.snapshots}
        snapshots: list[SyntheticOpportunitySnapshot] = []

        for series in dataset.series:
            feature = feature_by_stock.get(series.stock_id)
            quality_snapshot = quality_by_stock.get(series.stock_id)
            if feature is None or quality_snapshot is None:
                continue

            levels = SupportResistanceAnalyzer.analyze(
                series.stock_id,
                Timeframe.DAILY,
                list(series.bars),
            )
            context = EntryContextAnalyzer.analyze(list(series.bars), levels)
            entry_quality = EntryQualityScorer.score(context)
            stock_quality = StockQualityScore(
                fundamental_score=quality_snapshot.fundamental_score,
                technical_score=quality_snapshot.technical_score,
                total_score=quality_snapshot.total_score,
            )
            classification = OpportunityClassifier.classify(
                stock_quality,
                entry_quality,
            )

            snapshots.append(
                SyntheticOpportunitySnapshot(
                    symbol=series.symbol,
                    stock_id=series.stock_id,
                    stock_quality_score=quality_snapshot.total_score,
                    entry_quality_score=entry_quality,
                    classification=classification.classification,
                )
            )

        return SyntheticOpportunityReport(
            scenario_name=dataset.scenario.name,
            seed=dataset.scenario.seed,
            snapshots=tuple(snapshots),
        )
