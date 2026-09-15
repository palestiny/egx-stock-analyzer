from uuid import UUID

from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.technical_analysis.result import TechnicalAnalysisResult


class TechnicalAnalysisOrchestrator:
    @staticmethod
    def analyze(
        stock_id: UUID,
        timeframe: Timeframe,
        price_bars: list[PriceBar],
        momentum_lookback: int,
        volume_lookback: int,
    ) -> TechnicalAnalysisResult:
        raise NotImplementedError
