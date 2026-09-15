from dataclasses import dataclass
from uuid import UUID

from app.domain.market_data.timeframe import Timeframe
from app.domain.technical_analysis.momentum import MomentumEvidence
from app.domain.technical_analysis.support_resistance import SupportResistanceEvidence
from app.domain.technical_analysis.trend import TrendEvidence
from app.domain.technical_analysis.volume import VolumeEvidence


@dataclass(frozen=True)
class TechnicalAnalysisResult:
    stock_id: UUID
    timeframe: Timeframe
    trend: TrendEvidence
    support_resistance: SupportResistanceEvidence
    momentum: MomentumEvidence
    volume: VolumeEvidence
