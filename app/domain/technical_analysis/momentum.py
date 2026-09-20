from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID

from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe


class MomentumStatus(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    INSUFFICIENT_DATA = "insufficient_data"
    UNDEFINED = "undefined"


@dataclass(frozen=True)
class MomentumEvidence:
    status: MomentumStatus
    rate_of_change: Decimal | None = None


class MomentumAnalyzer:
    @staticmethod
    def analyze(
        stock_id: UUID,
        timeframe: Timeframe,
        price_bars: list[PriceBar],
        lookback: int,
    ) -> MomentumEvidence:

        if len(price_bars) < lookback + 1:
            return MomentumEvidence(
                status=MomentumStatus.INSUFFICIENT_DATA,
            )

        current_close = price_bars[-1].close.value
        comparison_close = price_bars[-(lookback + 1)].close.value

        if comparison_close == 0:
            return MomentumEvidence(
                status=MomentumStatus.UNDEFINED,
            )

        rate_of_change = (
            (current_close - comparison_close)
            / comparison_close
        ) * Decimal("100")

        if rate_of_change > 0:
            status = MomentumStatus.POSITIVE
        elif rate_of_change < 0:
            status = MomentumStatus.NEGATIVE
        else:
            status = MomentumStatus.NEUTRAL

        return MomentumEvidence(
            status=status,
            rate_of_change=rate_of_change,
        )