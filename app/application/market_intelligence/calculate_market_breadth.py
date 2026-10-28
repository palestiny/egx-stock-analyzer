from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from app.application.analysis.result_store import AnalysisResultStore
from app.application.clock import EGX_TIMEZONE, egx_today
from app.domain.technical_analysis.momentum import MomentumStatus
from app.domain.technical_analysis.trend import TrendStatus
from app.domain.technical_analysis.volume import VolumeStatus


@dataclass(frozen=True)
class MarketBreadthSnapshot:
    requested_symbols: int
    analyzed_symbols: int
    missing_symbols: tuple[str, ...]
    uptrend_count: int
    downtrend_count: int
    positive_momentum_count: int
    negative_momentum_count: int
    above_average_volume_count: int
    negative_momentum_with_above_average_volume_count: int
    bullish_breadth_percent: Decimal | None
    bearish_pressure_percent: Decimal | None
    stress_score: int | None
    stress_level: str
    data_status: str = "LATEST_SAVED_ANALYSIS_SNAPSHOT"
    analysis_dates_by_symbol: dict[str, date | None] | None = None
    undated_symbols: tuple[str, ...] = ()
    analysis_date_status: str = "UNKNOWN"
    latest_analysis_date: date | None = None
    as_of_date: date | None = None
    snapshot_age_calendar_days_by_symbol: dict[str, int | None] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_symbols": self.requested_symbols,
            "analyzed_symbols": self.analyzed_symbols,
            "missing_symbols": list(self.missing_symbols),
            "coverage_percent": _percent(self.analyzed_symbols, self.requested_symbols),
            "uptrend_count": self.uptrend_count,
            "downtrend_count": self.downtrend_count,
            "positive_momentum_count": self.positive_momentum_count,
            "negative_momentum_count": self.negative_momentum_count,
            "above_average_volume_count": self.above_average_volume_count,
            "negative_momentum_with_above_average_volume_count": self.negative_momentum_with_above_average_volume_count,
            "stress_components": {
                "downtrend": {
                    "count": self.downtrend_count,
                    "share_percent": _percent(self.downtrend_count, self.analyzed_symbols),
                    "weight_points": _weighted_points(
                        self.downtrend_count, self.analyzed_symbols, Decimal("50")
                    ),
                },
                "negative_momentum": {
                    "count": self.negative_momentum_count,
                    "share_percent": _percent(self.negative_momentum_count, self.analyzed_symbols),
                    "weight_points": _weighted_points(
                        self.negative_momentum_count, self.analyzed_symbols, Decimal("40")
                    ),
                },
                "negative_momentum_with_above_average_volume": {
                    "count": self.negative_momentum_with_above_average_volume_count,
                    "share_percent": _percent(
                        self.negative_momentum_with_above_average_volume_count,
                        self.analyzed_symbols,
                    ),
                    "weight_points": _weighted_points(
                        self.negative_momentum_with_above_average_volume_count,
                        self.analyzed_symbols,
                        Decimal("10"),
                    ),
                },
            },
            "bullish_breadth_percent": str(self.bullish_breadth_percent) if self.bullish_breadth_percent is not None else None,
            "bearish_pressure_percent": str(self.bearish_pressure_percent) if self.bearish_pressure_percent is not None else None,
            "stress_score": self.stress_score,
            "stress_level": self.stress_level,
            "data_status": self.data_status,
            "analysis_dates_by_symbol": {
                symbol: value.isoformat() if value is not None else None
                for symbol, value in (self.analysis_dates_by_symbol or {}).items()
            },
            "undated_symbols": list(self.undated_symbols),
            "analysis_date_status": self.analysis_date_status,
            "latest_analysis_date": (
                self.latest_analysis_date.isoformat()
                if self.latest_analysis_date is not None
                else None
            ),
            "as_of_date": self.as_of_date.isoformat() if self.as_of_date is not None else None,
            "snapshot_age_calendar_days_by_symbol": (
                self.snapshot_age_calendar_days_by_symbol or {}
            ),
            "methodology_version": "stress-heuristic-v1",
            "is_trading_signal": False,
            "methodology": "Stress is a heuristic: 50% downtrend share + 40% negative-momentum share + 10% negative-momentum-with-above-average-volume share. Percentages use analyzed symbols only.",
        }


def _weighted_points(numerator: int, denominator: int, weight: Decimal) -> str | None:
    if denominator <= 0:
        return None
    contribution = (Decimal(numerator) * weight / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return str(contribution)


def _percent(numerator: int, denominator: int) -> str | None:
    if denominator <= 0:
        return None
    value = (Decimal(numerator) * Decimal("100") / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return str(value)


@dataclass(frozen=True)
class CalculateMarketBreadth:
    result_store: AnalysisResultStore

    def execute(
        self, symbols: list[str], *, as_of_date: date | None = None
    ) -> MarketBreadthSnapshot:
        reference_date = as_of_date or egx_today()
        normalized = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        if not normalized:
            raise ValueError("At least one stock symbol is required")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate stock symbol in market breadth request")

        missing: list[str] = []
        analysis_dates: dict[str, date | None] = {}
        uptrend = downtrend = positive = negative = above_average = 0
        negative_with_volume = 0
        analyzed = 0

        for symbol in normalized:
            record = self.result_store.get_record(symbol)
            if record is None:
                missing.append(symbol)
                continue
            analyzed += 1
            raw_analysis_date = getattr(record, "analysis_date", None)
            if isinstance(raw_analysis_date, datetime):
                if raw_analysis_date.tzinfo is not None and raw_analysis_date.utcoffset() is not None:
                    raw_analysis_date = raw_analysis_date.astimezone(EGX_TIMEZONE).date()
                else:
                    raw_analysis_date = raw_analysis_date.date()
            analysis_dates[symbol] = (
                raw_analysis_date if isinstance(raw_analysis_date, date) else None
            )
            technical = record.result.technical_analysis
            if technical.trend.status is TrendStatus.UPTREND:
                uptrend += 1
            elif technical.trend.status is TrendStatus.DOWNTREND:
                downtrend += 1

            if technical.momentum.status is MomentumStatus.POSITIVE:
                positive += 1
            elif technical.momentum.status is MomentumStatus.NEGATIVE:
                negative += 1

            if technical.volume.status is VolumeStatus.ABOVE_AVERAGE:
                above_average += 1
                if technical.momentum.status is MomentumStatus.NEGATIVE:
                    negative_with_volume += 1

        if analyzed == 0:
            stress_score = None
            stress_level = "insufficient_data"
            bullish = bearish = None
        else:
            stress_value = (
                Decimal(downtrend) / Decimal(analyzed) * Decimal("50")
                + Decimal(negative) / Decimal(analyzed) * Decimal("40")
                + Decimal(negative_with_volume) / Decimal(analyzed) * Decimal("10")
            )
            stress_score = int(stress_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            stress_score = max(0, min(100, stress_score))
            stress_level = (
                "calm" if stress_score < 25 else
                "mixed" if stress_score < 50 else
                "elevated" if stress_score < 75 else
                "high"
            )
            bullish = (
                Decimal(uptrend + positive) * Decimal("50") / Decimal(analyzed)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            bearish = (
                Decimal(downtrend + negative) * Decimal("50") / Decimal(analyzed)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        known_dates = {value for value in analysis_dates.values() if value is not None}
        snapshot_ages = {
            symbol: (reference_date - value).days if value is not None else None
            for symbol, value in analysis_dates.items()
        }
        undated_symbols = tuple(
            symbol for symbol, value in analysis_dates.items() if value is None
        )
        if missing or (undated_symbols and known_dates):
            analysis_date_status = "PARTIAL"
        elif not known_dates:
            analysis_date_status = "UNKNOWN"
        elif len(known_dates) > 1:
            analysis_date_status = "MIXED"
        else:
            analysis_date_status = "CONSISTENT"

        return MarketBreadthSnapshot(
            requested_symbols=len(normalized),
            analyzed_symbols=analyzed,
            missing_symbols=tuple(missing),
            uptrend_count=uptrend,
            downtrend_count=downtrend,
            positive_momentum_count=positive,
            negative_momentum_count=negative,
            above_average_volume_count=above_average,
            negative_momentum_with_above_average_volume_count=negative_with_volume,
            bullish_breadth_percent=bullish,
            bearish_pressure_percent=bearish,
            stress_score=stress_score,
            stress_level=stress_level,
            analysis_dates_by_symbol=analysis_dates,
            undated_symbols=undated_symbols,
            analysis_date_status=analysis_date_status,
            latest_analysis_date=max(known_dates) if known_dates else None,
            as_of_date=reference_date,
            snapshot_age_calendar_days_by_symbol=snapshot_ages,
        )
