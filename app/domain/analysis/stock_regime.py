from dataclasses import dataclass
from enum import Enum
from math import sqrt
from statistics import pstdev

from app.domain.market_data.price_bar import PriceBar


class TrendRegime(Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    UPTREND = "uptrend"
    SIDEWAYS = "sideways"
    DOWNTREND = "downtrend"


class VolatilityRegime(Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class StockRiskProfile:
    trend: TrendRegime
    volatility: VolatilityRegime
    observation_count: int
    latest_close: float | None
    sma_20: float | None
    sma_50: float | None
    annualized_realized_volatility: float | None
    drawdown_from_observed_peak: float | None
    reasons: tuple[str, ...]


class StockRegimeAnalyzer:
    """Descriptive, trailing-window price regime metrics; not a trading signal."""

    MINIMUM_BARS = 50
    TRADING_SESSIONS_PER_YEAR = 252
    HIGH_VOLATILITY_THRESHOLD = 0.40
    MODERATE_VOLATILITY_THRESHOLD = 0.20

    @classmethod
    def analyze(cls, price_bars: list[PriceBar]) -> StockRiskProfile:
        cls._validate_bars(price_bars)
        count = len(price_bars)
        if count < cls.MINIMUM_BARS:
            return StockRiskProfile(
                trend=TrendRegime.INSUFFICIENT_DATA,
                volatility=VolatilityRegime.INSUFFICIENT_DATA,
                observation_count=count,
                latest_close=float(price_bars[-1].close.value) if price_bars else None,
                sma_20=None,
                sma_50=None,
                annualized_realized_volatility=None,
                drawdown_from_observed_peak=None,
                reasons=(f"At least {cls.MINIMUM_BARS} daily bars are required.",),
            )

        closes = [float(bar.close.value) for bar in price_bars]
        latest = closes[-1]
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50
        prior_sma_20 = sum(closes[-21:-1]) / 20
        if latest > sma_20 and sma_20 > sma_50 and sma_20 > prior_sma_20:
            trend = TrendRegime.UPTREND
            trend_reason = "Close is above SMA20, SMA20 is above SMA50, and SMA20 is rising."
        elif latest < sma_20 and sma_20 < sma_50 and sma_20 < prior_sma_20:
            trend = TrendRegime.DOWNTREND
            trend_reason = "Close is below SMA20, SMA20 is below SMA50, and SMA20 is falling."
        else:
            trend = TrendRegime.SIDEWAYS
            trend_reason = "The trailing moving-average conditions do not confirm a directional trend."

        returns = [(current / previous) - 1 for previous, current in zip(closes, closes[1:])]
        volatility = pstdev(returns) * sqrt(cls.TRADING_SESSIONS_PER_YEAR)
        if volatility >= cls.HIGH_VOLATILITY_THRESHOLD:
            volatility_regime = VolatilityRegime.HIGH
        elif volatility >= cls.MODERATE_VOLATILITY_THRESHOLD:
            volatility_regime = VolatilityRegime.MODERATE
        else:
            volatility_regime = VolatilityRegime.LOW

        peak = max(closes)
        drawdown = latest / peak - 1 if peak > 0 else 0.0
        return StockRiskProfile(
            trend=trend,
            volatility=volatility_regime,
            observation_count=count,
            latest_close=latest,
            sma_20=sma_20,
            sma_50=sma_50,
            annualized_realized_volatility=volatility,
            drawdown_from_observed_peak=drawdown,
            reasons=(trend_reason, f"Annualized realized volatility is {volatility_regime.value}."),
        )

    @staticmethod
    def _validate_bars(price_bars: list[PriceBar]) -> None:
        if any(bar.close.value <= 0 for bar in price_bars):
            raise ValueError("Closing prices must be greater than zero.")
        if any(
            left.stock_id != right.stock_id or left.timeframe != right.timeframe
            for left, right in zip(price_bars, price_bars[1:])
        ):
            raise ValueError("All bars must belong to the same stock and timeframe.")
        if any(left.timestamp >= right.timestamp for left, right in zip(price_bars, price_bars[1:])):
            raise ValueError("Price bars must be strictly ordered by timestamp.")
