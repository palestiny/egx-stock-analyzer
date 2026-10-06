from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.market_data.timeframe import Timeframe
from app.domain.technical_analysis.momentum import MomentumAnalyzer
from app.domain.technical_analysis.scoring import TechnicalScorer
from app.domain.technical_analysis.support_resistance import SupportResistanceAnalyzer
from app.domain.technical_analysis.trend import TrendAnalyzer
from app.domain.technical_analysis.volume import VolumeAnalyzer

from .generator import SyntheticDataset


@dataclass(frozen=True)
class SyntheticFeatureSnapshot:
    symbol: str
    stock_id: UUID
    trend: str
    momentum: str
    momentum_percent: float | None
    volume: str
    volume_ratio: float | None
    support_count: int
    resistance_count: int
    technical_score: int
    regime: str


@dataclass(frozen=True)
class SyntheticFeatureReport:
    scenario_name: str
    seed: int
    snapshots: tuple[SyntheticFeatureSnapshot, ...]

    @property
    def positive_score_count(self) -> int:
        return sum(snapshot.technical_score > 0 for snapshot in self.snapshots)


class SyntheticFeatureHarness:
    """Runs existing production-domain analyzers against synthetic scenarios.

    This is an integration harness, not a replacement analytical engine.
    """

    def run(
        self,
        dataset: SyntheticDataset,
        *,
        momentum_lookback: int = 20,
        volume_lookback: int = 20,
    ) -> SyntheticFeatureReport:
        snapshots: list[SyntheticFeatureSnapshot] = []

        for series in dataset.series:
            bars = list(series.bars)
            trend = TrendAnalyzer.analyze(
                series.stock_id, Timeframe.DAILY, bars
            )
            momentum = MomentumAnalyzer.analyze(
                series.stock_id, Timeframe.DAILY, bars, momentum_lookback
            )
            volume = VolumeAnalyzer.analyze(
                series.stock_id, Timeframe.DAILY, bars, volume_lookback
            )
            levels = SupportResistanceAnalyzer.analyze(
                series.stock_id, Timeframe.DAILY, bars
            )
            score = TechnicalScorer.score(trend, momentum, volume)

            snapshots.append(
                SyntheticFeatureSnapshot(
                    symbol=series.symbol,
                    stock_id=series.stock_id,
                    trend=trend.status.value,
                    momentum=momentum.status.value,
                    momentum_percent=(
                        float(momentum.rate_of_change)
                        if momentum.rate_of_change is not None
                        else None
                    ),
                    volume=volume.status.value,
                    volume_ratio=(
                        float(volume.volume_ratio)
                        if volume.volume_ratio is not None
                        else None
                    ),
                    support_count=len(levels.support_levels),
                    resistance_count=len(levels.resistance_levels),
                    technical_score=score.total_score,
                    regime=series.regimes[-1].value,
                )
            )

        return SyntheticFeatureReport(
            scenario_name=dataset.scenario.name,
            seed=dataset.scenario.seed,
            snapshots=tuple(snapshots),
        )
