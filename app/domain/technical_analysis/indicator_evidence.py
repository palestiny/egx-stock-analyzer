from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class TechnicalIndicatorPoint:
    timestamp: datetime
    close: Decimal
    sma_20: Decimal | None
    sma_50: Decimal | None
    sma_200: Decimal | None
    ema_9: Decimal | None
    ema_20: Decimal | None
    ema_50: Decimal | None
    ema_200: Decimal | None
    rsi_14: Decimal | None
    macd_line: Decimal | None
    macd_signal: Decimal | None
    macd_histogram: Decimal | None
    bollinger_upper: Decimal | None
    bollinger_middle: Decimal | None
    bollinger_lower: Decimal | None
    atr_14: Decimal | None
    stochastic_k_14: Decimal | None
    stochastic_d_3: Decimal | None
    cci_20: Decimal | None
    obv: int | None
    mfi_14: Decimal | None
    plus_di_14: Decimal | None
    minus_di_14: Decimal | None
    adx_14: Decimal | None
    ichimoku_conversion_9: Decimal | None
    ichimoku_base_26: Decimal | None
    ichimoku_span_a_unshifted: Decimal | None
    ichimoku_span_b_unshifted: Decimal | None
    candlestick_patterns: tuple[str, ...]


@dataclass(frozen=True)
class TechnicalIndicatorEvidence:
    points: tuple[TechnicalIndicatorPoint, ...]
    methodology_version: str = "technical-indicators-v1"

    @property
    def latest(self) -> TechnicalIndicatorPoint | None:
        return self.points[-1] if self.points else None
