from dataclasses import dataclass
from decimal import Decimal

from app.application.analysis.result_store import AnalysisResultStore
from app.domain.market_intelligence.breakout import (
    BreakoutDirection,
    BreakoutMatch,
    BreakoutScanResult,
    BreakoutStatus,
)
from app.domain.technical_analysis.trend import TrendStatus
from app.domain.technical_analysis.volume import VolumeStatus


@dataclass(frozen=True)
class ScanBreakouts:
    result_store: AnalysisResultStore

    def execute(
        self,
        symbols: list[str],
        tolerance_percent: Decimal = Decimal("1"),
        limit: int = 20,
    ) -> BreakoutScanResult:
        if tolerance_percent < 0:
            raise ValueError("tolerance_percent cannot be negative")
        if limit <= 0:
            raise ValueError("limit must be positive")

        normalized = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate stock symbol in breakout scanner")

        matches: list[BreakoutMatch] = []
        for symbol in normalized:
            record = self.result_store.get_record(symbol)
            if record is None:
                continue

            result = record.result
            entry = result.entry_context
            technical = result.technical_analysis
            if entry.current_price is None:
                continue

            current = entry.current_price.value
            resistance = entry.nearest_resistance
            support = entry.nearest_support

            if resistance is not None and resistance.price.value > 0:
                trigger = resistance.price.value
                distance = (current - trigger) / trigger * Decimal("100")
                near_threshold = distance >= -tolerance_percent
                confirmed = distance >= 0
                evidence: list[str] = [
                    "nearest_resistance_reference",
                ]
                score = int(result.stock_quality.total_score)

                if technical.trend.status is TrendStatus.UPTREND:
                    score += 10
                    evidence.append("uptrend")
                if technical.volume.status is VolumeStatus.ABOVE_AVERAGE:
                    score += 10
                    evidence.append("above_average_volume")
                if near_threshold and (confirmed or technical.trend.status is TrendStatus.UPTREND):
                    matches.append(
                        BreakoutMatch(
                            symbol=symbol,
                            direction=BreakoutDirection.UPSIDE,
                            status=BreakoutStatus.CONFIRMED if confirmed else BreakoutStatus.CANDIDATE,
                            trigger_price=trigger,
                            current_price=current,
                            distance_percent=distance,
                            score=min(score, 100),
                            evidence=tuple(evidence),
                        )
                    )

            if support is not None and support.price.value > 0:
                trigger = support.price.value
                distance = (current - trigger) / trigger * Decimal("100")
                near_threshold = distance <= tolerance_percent
                confirmed = distance <= 0
                evidence = ["nearest_support_reference"]
                score = int(result.stock_quality.total_score)

                if technical.trend.status is TrendStatus.DOWNTREND:
                    score += 10
                    evidence.append("downtrend")
                if technical.volume.status is VolumeStatus.ABOVE_AVERAGE:
                    score += 10
                    evidence.append("above_average_volume")
                if near_threshold and (confirmed or technical.trend.status is TrendStatus.DOWNTREND):
                    matches.append(
                        BreakoutMatch(
                            symbol=symbol,
                            direction=BreakoutDirection.DOWNSIDE,
                            status=BreakoutStatus.CONFIRMED if confirmed else BreakoutStatus.CANDIDATE,
                            trigger_price=trigger,
                            current_price=current,
                            distance_percent=distance,
                            score=min(score, 100),
                            evidence=tuple(evidence),
                        )
                    )

        matches.sort(key=lambda item: (-item.score, abs(item.distance_percent), item.symbol, item.direction.value))
        return BreakoutScanResult(
            matches=tuple(matches[:limit]),
            evaluated_symbols=len(normalized),
            data_status="HISTORICAL_ANALYSIS_RESULT",
        )
