from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe


class TrendStatus(Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class TrendEvidence:
    status: TrendStatus


class TrendAnalyzer:
    @staticmethod
    def analyze(
        stock_id: UUID,
        timeframe: Timeframe,
        price_bars: list[PriceBar],
    ) -> TrendEvidence:

        if len(price_bars) < 3:
            return TrendEvidence(TrendStatus.INSUFFICIENT_DATA)

        swing_highs: list = []
        swing_lows: list = []

        for index in range(1, len(price_bars) - 1):
            previous_bar = price_bars[index - 1]
            current_bar = price_bars[index]
            next_bar = price_bars[index + 1]

            if (
                current_bar.high.value > previous_bar.high.value
                and current_bar.high.value > next_bar.high.value
            ):
                swing_highs.append(current_bar.high.value)

            if (
                current_bar.low.value < previous_bar.low.value
                and current_bar.low.value < next_bar.low.value
            ):
                swing_lows.append(current_bar.low.value)

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return TrendEvidence(TrendStatus.INSUFFICIENT_DATA)

        higher_highs = all(
            current > previous
            for previous, current in zip(
                swing_highs,
                swing_highs[1:],
            )
        )

        higher_lows = all(
            current > previous
            for previous, current in zip(
                swing_lows,
                swing_lows[1:],
            )
        )

        lower_highs = all(
            current < previous
            for previous, current in zip(
                swing_highs,
                swing_highs[1:],
            )
        )

        lower_lows = all(
            current < previous
            for previous, current in zip(
                swing_lows,
                swing_lows[1:],
            )
        )

        if higher_highs and higher_lows:
            return TrendEvidence(TrendStatus.UPTREND)

        if lower_highs and lower_lows:
            return TrendEvidence(TrendStatus.DOWNTREND)

        return TrendEvidence(TrendStatus.SIDEWAYS)