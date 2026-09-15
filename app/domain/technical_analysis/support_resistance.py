from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe


@dataclass(frozen=True)
class PriceLevelEvidence:
    price: Price
    timestamp: datetime


@dataclass(frozen=True)
class SupportResistanceEvidence:
    support_levels: tuple[PriceLevelEvidence, ...]
    resistance_levels: tuple[PriceLevelEvidence, ...]


class SupportResistanceAnalyzer:
    @staticmethod
    def analyze(
        stock_id: UUID,
        timeframe: Timeframe,
        price_bars: list[PriceBar],
    ) -> SupportResistanceEvidence:
        support_levels: list[PriceLevelEvidence] = []
        resistance_levels: list[PriceLevelEvidence] = []

        if len(price_bars) < 3:
            return SupportResistanceEvidence(
                support_levels=(),
                resistance_levels=(),
            )

        for index in range(1, len(price_bars) - 1):
            previous_bar = price_bars[index - 1]
            current_bar = price_bars[index]
            next_bar = price_bars[index + 1]

            if (
                current_bar.low.value < previous_bar.low.value
                and current_bar.low.value < next_bar.low.value
            ):
                support_levels.append(
                    PriceLevelEvidence(
                        price=current_bar.low,
                        timestamp=current_bar.timestamp,
                    )
                )

            if (
                current_bar.high.value > previous_bar.high.value
                and current_bar.high.value > next_bar.high.value
            ):
                resistance_levels.append(
                    PriceLevelEvidence(
                        price=current_bar.high,
                        timestamp=current_bar.timestamp,
                    )
                )

        return SupportResistanceEvidence(
            support_levels=tuple(support_levels),
            resistance_levels=tuple(resistance_levels),
        )
