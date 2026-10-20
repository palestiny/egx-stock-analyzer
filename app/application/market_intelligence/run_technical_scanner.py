from dataclasses import dataclass
from decimal import Decimal

from app.application.analysis.result_store import AnalysisResultStore
from app.domain.market_intelligence.scanner import (
    ScannerCriterion,
    ScannerMatch,
    TechnicalScannerResult,
)
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.technical_analysis.momentum import MomentumStatus
from app.domain.technical_analysis.trend import TrendStatus
from app.domain.technical_analysis.volume import VolumeStatus


@dataclass(frozen=True)
class RunTechnicalScanner:
    result_store: AnalysisResultStore

    def execute(self, symbols: list[str], scanner_id: str = "trend-momentum-volume") -> TechnicalScannerResult:
        if not scanner_id.strip():
            raise ValueError("scanner_id is required")

        normalized = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate stock symbol in technical scanner")

        pre_breakout_mode = scanner_id == "pre-breakout-momentum-volume"
        matches: list[ScannerMatch] = []
        for symbol in normalized:
            record = self.result_store.get_record(symbol)
            if record is None:
                continue

            result = record.result
            technical = result.technical_analysis
            momentum = technical.momentum.rate_of_change
            volume_ratio = technical.volume.volume_ratio
            criteria = []
            if technical.trend.status is TrendStatus.UPTREND:
                criteria.append(ScannerCriterion.UPTREND)
            if technical.momentum.status is MomentumStatus.POSITIVE:
                criteria.append(ScannerCriterion.POSITIVE_MOMENTUM)
            if technical.volume.status is VolumeStatus.ABOVE_AVERAGE:
                criteria.append(ScannerCriterion.ABOVE_AVERAGE_VOLUME)
            if result.opportunity.classification in {
                OpportunityClassification.BUY,
            }:
                criteria.append(ScannerCriterion.ACTIONABLE_CLASSIFICATION)

            resistance_price = None
            distance_to_resistance_percent = None
            near_resistance = False
            if pre_breakout_mode:
                entry = result.entry_context
                current_price = (
                    entry.current_price.value
                    if entry is not None and entry.current_price is not None
                    else None
                )
                resistance = entry.nearest_resistance if entry is not None else None
                if current_price is not None and resistance is not None and resistance.price.value > 0:
                    resistance_price = resistance.price.value
                    distance_to_resistance_percent = (
                        (current_price - resistance_price) / resistance_price * Decimal("100")
                    )
                    # Watch only prices still below resistance, within 5%; a crossed level
                    # belongs to breakout confirmation, not the pre-breakout watchlist.
                    near_resistance = Decimal("-5") <= distance_to_resistance_percent < 0
                volume_expansion = volume_ratio is not None and volume_ratio >= Decimal("1.5")
                if volume_expansion:
                    criteria.append(ScannerCriterion.VOLUME_EXPANSION)
                if near_resistance:
                    criteria.append(ScannerCriterion.NEAR_RESISTANCE)
                qualifies = (
                    technical.momentum.status is MomentumStatus.POSITIVE
                    and volume_expansion
                    and near_resistance
                )
            else:
                qualifies = len(criteria) >= 3

            if qualifies:
                matches.append(
                    ScannerMatch(
                        symbol=symbol,
                        score=result.stock_quality.total_score,
                        criteria=tuple(criteria),
                        momentum_percent=momentum,
                        volume_ratio=volume_ratio,
                        resistance_price=resistance_price,
                        distance_to_resistance_percent=distance_to_resistance_percent,
                    )
                )

        if pre_breakout_mode:
            matches.sort(
                key=lambda item: (
                    -(item.volume_ratio or Decimal("0")),
                    -(item.momentum_percent or Decimal("0")),
                    -item.score,
                    item.symbol,
                )
            )
        else:
            matches.sort(key=lambda item: (-item.score, -len(item.criteria), item.symbol))
        return TechnicalScannerResult(
            scanner_id=scanner_id,
            matches=tuple(matches),
            evaluated_symbols=len(normalized),
            data_status="HISTORICAL_ANALYSIS_RESULT",
        )
