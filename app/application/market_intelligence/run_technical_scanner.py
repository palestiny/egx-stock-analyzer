from dataclasses import dataclass

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

        matches: list[ScannerMatch] = []
        for symbol in normalized:
            record = self.result_store.get_record(symbol)
            if record is None:
                continue

            result = record.result
            technical = result.technical_analysis
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

            if len(criteria) >= 3:
                matches.append(
                    ScannerMatch(
                        symbol=symbol,
                        score=result.stock_quality.total_score,
                        criteria=tuple(criteria),
                    )
                )

        matches.sort(key=lambda item: (-item.score, -len(item.criteria), item.symbol))
        return TechnicalScannerResult(
            scanner_id=scanner_id,
            matches=tuple(matches),
            evaluated_symbols=len(normalized),
            data_status="HISTORICAL_ANALYSIS_RESULT",
        )
