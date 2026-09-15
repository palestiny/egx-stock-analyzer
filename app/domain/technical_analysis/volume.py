from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID

from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe


class VolumeStatus(Enum):
    ABOVE_AVERAGE = "above_average"
    BELOW_AVERAGE = "below_average"
    EQUAL_TO_AVERAGE = "equal_to_average"
    INSUFFICIENT_DATA = "insufficient_data"
    UNDEFINED = "undefined"


@dataclass(frozen=True)
class VolumeEvidence:
    status: VolumeStatus
    volume_ratio: Decimal | None = None


class VolumeAnalyzer:
    @staticmethod
    def analyze(
        stock_id: UUID,
        timeframe: Timeframe,
        price_bars: list[PriceBar],
        lookback: int,
    ) -> VolumeEvidence:
        if len(price_bars) < lookback + 1:
            return VolumeEvidence(
                status=VolumeStatus.INSUFFICIENT_DATA,
            )

        current_volume = price_bars[-1].volume.value
        previous_volumes = [
            bar.volume.value
            for bar in price_bars[-(lookback + 1):-1]
        ]

        average_previous_volume = (
            Decimal(sum(previous_volumes)) / Decimal(lookback)
        )

        if average_previous_volume == 0:
            return VolumeEvidence(
                status=VolumeStatus.UNDEFINED,
            )

        volume_ratio = Decimal(current_volume) / average_previous_volume

        if volume_ratio > 1:
            status = VolumeStatus.ABOVE_AVERAGE
        elif volume_ratio < 1:
            status = VolumeStatus.BELOW_AVERAGE
        else:
            status = VolumeStatus.EQUAL_TO_AVERAGE

        return VolumeEvidence(
            status=status,
            volume_ratio=volume_ratio,
        )
