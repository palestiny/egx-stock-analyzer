from dataclasses import dataclass

from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus


@dataclass(frozen=True)
class TechnicalScore:
    trend_points: int
    momentum_points: int
    volume_points: int
    total_score: int


class TechnicalScorer:
    @staticmethod
    def score(
        trend: TrendEvidence,
        momentum: MomentumEvidence,
        volume: VolumeEvidence,
    ) -> TechnicalScore:
        trend_points = {
            TrendStatus.UPTREND: 1,
            TrendStatus.SIDEWAYS: 0,
            TrendStatus.DOWNTREND: -1,
            TrendStatus.INSUFFICIENT_DATA: 0,
        }[trend.status]

        momentum_points = {
            MomentumStatus.POSITIVE: 1,
            MomentumStatus.NEUTRAL: 0,
            MomentumStatus.NEGATIVE: -1,
            MomentumStatus.INSUFFICIENT_DATA: 0,
            MomentumStatus.UNDEFINED: 0,
        }[momentum.status]

        volume_points = {
            VolumeStatus.ABOVE_AVERAGE: 1,
            VolumeStatus.EQUAL_TO_AVERAGE: 0,
            VolumeStatus.BELOW_AVERAGE: -1,
            VolumeStatus.INSUFFICIENT_DATA: 0,
            VolumeStatus.UNDEFINED: 0,
        }[volume.status]

        return TechnicalScore(
            trend_points=trend_points,
            momentum_points=momentum_points,
            volume_points=volume_points,
            total_score=trend_points + momentum_points + volume_points,
        )
