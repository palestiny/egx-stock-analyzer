from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from statistics import pstdev
from uuid import UUID

from app.domain.market_data.price_bar import PriceBar


class StressLevel(Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True)
class CrashRadarSignal:
    stock_id: UUID
    return_percent: Decimal
    volatility_percent: Decimal
    volume_ratio: Decimal
    score: int
    level: StressLevel

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")
        if self.volume_ratio < 0 or self.volatility_percent < 0:
            raise ValueError("volatility and volume ratio cannot be negative")


@dataclass(frozen=True)
class MarketStressSnapshot:
    symbol_count: int
    decliner_ratio: Decimal
    average_return_percent: Decimal
    high_volatility_ratio: Decimal
    crash_ratio: Decimal
    score: int
    level: StressLevel

    def __post_init__(self) -> None:
        if self.symbol_count < 0:
            raise ValueError("symbol_count cannot be negative")
        for value in (
            self.decliner_ratio,
            self.high_volatility_ratio,
            self.crash_ratio,
        ):
            if not Decimal("0") <= value <= Decimal("1"):
                raise ValueError("market ratios must be between 0 and 1")
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")


class CrashRadarAnalyzer:
    """Deterministic crash-risk signal from price, volatility and volume."""

    @staticmethod
    def analyze(stock_id: UUID, bars: list[PriceBar], *, lookback: int = 20) -> CrashRadarSignal:
        if len(bars) < max(lookback, 2) + 1:
            raise ValueError("insufficient bars for crash radar")

        ordered = sorted(bars, key=lambda bar: bar.timestamp)
        window = ordered[-(lookback + 1):]
        returns = [
            (float(current.close.value / previous.close.value) - 1.0) * 100.0
            for previous, current in zip(window, window[1:])
        ]
        return_percent = Decimal(str(returns[-1]))
        volatility_percent = Decimal(str(pstdev(returns) if len(returns) > 1 else 0.0))
        average_volume = sum(bar.volume.value for bar in window[:-1]) / len(window[:-1])
        volume_ratio = (
            Decimal(str(window[-1].volume.value / average_volume))
            if average_volume
            else Decimal("0")
        )

        score = 0
        score += min(45, int(max(0.0, -float(return_percent)) * 9))
        score += min(30, int(max(0.0, float(volatility_percent) - 1.5) * 6))
        score += min(25, int(max(0.0, float(volume_ratio) - 1.0) * 10))
        score = min(100, score)

        if score >= 75:
            level = StressLevel.EXTREME
        elif score >= 50:
            level = StressLevel.HIGH
        elif score >= 25:
            level = StressLevel.ELEVATED
        else:
            level = StressLevel.NORMAL

        return CrashRadarSignal(
            stock_id=stock_id,
            return_percent=return_percent,
            volatility_percent=volatility_percent,
            volume_ratio=volume_ratio,
            score=score,
            level=level,
        )


class MarketStressAnalyzer:
    """Aggregates cross-sectional stress; isolated stock shocks do not define market stress."""

    @staticmethod
    def analyze(signals: list[CrashRadarSignal]) -> MarketStressSnapshot:
        if not signals:
            return MarketStressSnapshot(
                symbol_count=0,
                decliner_ratio=Decimal("0"),
                average_return_percent=Decimal("0"),
                high_volatility_ratio=Decimal("0"),
                crash_ratio=Decimal("0"),
                score=0,
                level=StressLevel.NORMAL,
            )

        count = len(signals)
        decliners = sum(signal.return_percent < 0 for signal in signals)
        high_volatility = sum(signal.volatility_percent >= Decimal("3") for signal in signals)
        crashes = sum(signal.level in (StressLevel.HIGH, StressLevel.EXTREME) for signal in signals)

        decliner_ratio = Decimal(decliners) / Decimal(count)
        high_volatility_ratio = Decimal(high_volatility) / Decimal(count)
        crash_ratio = Decimal(crashes) / Decimal(count)
        average_return = sum(
            (signal.return_percent for signal in signals), Decimal("0")
        ) / Decimal(count)

        score = min(
            100,
            int(
                decliner_ratio * 45
                + high_volatility_ratio * 25
                + crash_ratio * 20
                + max(Decimal("0"), -average_return) * Decimal("5")
            ),
        )

        if score >= 75:
            level = StressLevel.EXTREME
        elif score >= 50:
            level = StressLevel.HIGH
        elif score >= 25:
            level = StressLevel.ELEVATED
        else:
            level = StressLevel.NORMAL

        return MarketStressSnapshot(
            symbol_count=count,
            decliner_ratio=decliner_ratio,
            average_return_percent=average_return,
            high_volatility_ratio=high_volatility_ratio,
            crash_ratio=crash_ratio,
            score=score,
            level=level,
        )
