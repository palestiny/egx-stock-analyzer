from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal

from app.application.analysis.result_store import AnalysisResultStore
from app.domain.signals.model import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)
from app.domain.technical_analysis.trend import TrendStatus


@dataclass(frozen=True)
class GenerateSignal:
    result_store: AnalysisResultStore

    def execute(self, symbol: str) -> Signal | None:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol is required")

        record = self.result_store.get_record(normalized)
        if record is None:
            return None
        result = record.result
        entry = result.entry_context
        current_price = entry.current_price
        if current_price is None:
            return None
        current = current_price.value
        technical = result.technical_analysis
        now = datetime.combine(
            record.analysis_date or datetime.now(timezone.utc).date(),
            time.min,
            tzinfo=timezone.utc,
        )

        resistance = entry.nearest_resistance
        support = entry.nearest_support
        trend = technical.trend.status

        if trend is TrendStatus.UPTREND and resistance is not None and current >= resistance.price.value:
            direction = SignalDirection.BUY
            invalidation = support.price.value if support is not None else current * Decimal("0.97")
            risk = current - invalidation
            if risk <= 0:
                return None
            targets = (
                Target(current + risk, "T1"),
                Target(current + risk * Decimal("2"), "T2"),
            )
            evidence = [
                SignalEvidence("breakout", f"Price {current} is above resistance {resistance.price.value}"),
                SignalEvidence("trend", "Underlying trend is uptrend"),
            ]
            if technical.volume.status.value == "above_average":
                evidence.append(SignalEvidence("volume", "Volume is above average", Decimal("0.5")))
        elif trend is TrendStatus.DOWNTREND and support is not None and current <= support.price.value:
            direction = SignalDirection.SELL
            invalidation = resistance.price.value if resistance is not None else current * Decimal("1.03")
            risk = invalidation - current
            if risk <= 0:
                return None
            targets = (
                Target(max(Decimal("0.0001"), current - risk), "T1"),
                Target(max(Decimal("0.0001"), current - risk * Decimal("2")), "T2"),
            )
            evidence = [
                SignalEvidence("breakdown", f"Price {current} is below support {support.price.value}"),
                SignalEvidence("trend", "Underlying trend is downtrend"),
            ]
            if technical.volume.status.value == "above_average":
                evidence.append(SignalEvidence("volume", "Volume is above average", Decimal("0.5")))
        else:
            return None

        confidence = Decimal(min(100, max(0, int(result.stock_quality.total_score))))
        risk_score = Decimal(min(100, max(0, int(100 - confidence))))
        half = current * Decimal("0.005")
        return Signal(
            symbol=normalized,
            direction=direction,
            status=SignalStatus.ACTIVE,
            generated_at=now,
            timeframe=str(technical.timeframe.value),
            entry_zone=PriceZone(current - half, current + half),
            invalidation=invalidation,
            targets=targets,
            confidence=confidence,
            risk_score=risk_score,
            evidence=tuple(evidence),
            strategy_id="breakout-trend",
            strategy_version="1.0",
            data_timestamp=now,
        )
