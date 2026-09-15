from uuid import UUID

from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.technical_analysis.momentum import MomentumAnalyzer
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.support_resistance import SupportResistanceAnalyzer
from app.domain.technical_analysis.trend import TrendAnalyzer
from app.domain.technical_analysis.volume import VolumeAnalyzer


class TechnicalAnalysisOrchestrator:
    @staticmethod
    def analyze(
        stock_id: UUID,
        timeframe: Timeframe,
        price_bars: list[PriceBar],
        momentum_lookback: int,
        volume_lookback: int,
    ) -> TechnicalAnalysisResult:
        trend = TrendAnalyzer.analyze(
            stock_id,
            timeframe,
            price_bars,
        )

        support_resistance = SupportResistanceAnalyzer.analyze(
            stock_id,
            timeframe,
            price_bars,
        )

        momentum = MomentumAnalyzer.analyze(
            stock_id,
            timeframe,
            price_bars,
            momentum_lookback,
        )

        volume = VolumeAnalyzer.analyze(
            stock_id,
            timeframe,
            price_bars,
            volume_lookback,
        )

        return TechnicalAnalysisResult(
            stock_id=stock_id,
            timeframe=timeframe,
            trend=trend,
            support_resistance=support_resistance,
            momentum=momentum,
            volume=volume,
        )
