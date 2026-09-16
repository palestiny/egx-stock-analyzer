from dataclasses import dataclass

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.technical_analysis.support_resistance import (
    PriceLevelEvidence,
    SupportResistanceEvidence,
)


@dataclass(frozen=True)
class EntryContext:
    current_price: Price | None
    nearest_support: PriceLevelEvidence | None
    nearest_resistance: PriceLevelEvidence | None


class EntryContextAnalyzer:
    @staticmethod
    def analyze(
        price_bars: list[PriceBar],
        support_resistance: SupportResistanceEvidence,
    ) -> EntryContext:
        if not price_bars:
            return EntryContext(
                current_price=None,
                nearest_support=None,
                nearest_resistance=None,
            )

        current_price = price_bars[-1].close
        current_value = current_price.value

        supports = [
            level
            for level in support_resistance.support_levels
            if level.price.value <= current_value
        ]
        resistances = [
            level
            for level in support_resistance.resistance_levels
            if level.price.value >= current_value
        ]

        nearest_support = (
            max(supports, key=lambda level: level.price.value)
            if supports
            else None
        )
        nearest_resistance = (
            min(resistances, key=lambda level: level.price.value)
            if resistances
            else None
        )

        return EntryContext(
            current_price=current_price,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
        )
