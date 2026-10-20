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

    @staticmethod
    def _quality_score(*, confirmed: bool, trend_aligned: bool, volume_confirmed: bool, stock_quality: int) -> int:
        """Score evidence completeness, not the probability of a profitable trade."""
        score = 30 if confirmed else 20
        if trend_aligned:
            score += 25
        if volume_confirmed:
            score += 25
        score += round(max(0, min(stock_quality, 100)) * 0.20)
        return min(score, 100)

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
            stock_quality = int(result.stock_quality.total_score)
            volume_confirmed = technical.volume.status is VolumeStatus.ABOVE_AVERAGE

            if resistance is not None and resistance.price.value > 0:
                trigger = resistance.price.value
                distance = (current - trigger) / trigger * Decimal("100")
                near_threshold = distance >= -tolerance_percent
                confirmed = distance >= 0
                trend_aligned = technical.trend.status is TrendStatus.UPTREND
                evidence: list[str] = [
                    "nearest_resistance_reference",
                    "trigger_confirmed" if confirmed else "near_trigger",
                ]
                if trend_aligned:
                    evidence.append("trend_aligned")
                if volume_confirmed:
                    evidence.append("above_average_volume")
                if near_threshold and (confirmed or trend_aligned):
                    matches.append(
                        BreakoutMatch(
                            symbol=symbol,
                            direction=BreakoutDirection.UPSIDE,
                            status=BreakoutStatus.CONFIRMED if confirmed else BreakoutStatus.CANDIDATE,
                            trigger_price=trigger,
                            current_price=current,
                            distance_percent=distance,
                            score=self._quality_score(
                                confirmed=confirmed,
                                trend_aligned=trend_aligned,
                                volume_confirmed=volume_confirmed,
                                stock_quality=stock_quality,
                            ),
                            evidence=tuple(evidence),
                        )
                    )

            if support is not None and support.price.value > 0:
                trigger = support.price.value
                distance = (current - trigger) / trigger * Decimal("100")
                near_threshold = distance <= tolerance_percent
                confirmed = distance <= 0
                trend_aligned = technical.trend.status is TrendStatus.DOWNTREND
                evidence = [
                    "nearest_support_reference",
                    "trigger_confirmed" if confirmed else "near_trigger",
                ]
                if trend_aligned:
                    evidence.append("trend_aligned")
                if volume_confirmed:
                    evidence.append("above_average_volume")
                if near_threshold and (confirmed or trend_aligned):
                    matches.append(
                        BreakoutMatch(
                            symbol=symbol,
                            direction=BreakoutDirection.DOWNSIDE,
                            status=BreakoutStatus.CONFIRMED if confirmed else BreakoutStatus.CANDIDATE,
                            trigger_price=trigger,
                            current_price=current,
                            distance_percent=distance,
                            score=self._quality_score(
                                confirmed=confirmed,
                                trend_aligned=trend_aligned,
                                volume_confirmed=volume_confirmed,
                                stock_quality=stock_quality,
                            ),
                            evidence=tuple(evidence),
                        )
                    )

        matches.sort(key=lambda item: (-item.score, abs(item.distance_percent), item.symbol, item.direction.value))
        return BreakoutScanResult(
            matches=tuple(matches[:limit]),
            evaluated_symbols=len(normalized),
            data_status="HISTORICAL_ANALYSIS_RESULT",
        )
