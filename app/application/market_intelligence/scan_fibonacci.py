from dataclasses import dataclass
from decimal import Decimal

from app.application.analysis.result_store import AnalysisResultStore
from app.domain.market_intelligence.fibonacci import FibonacciOpportunity, FibonacciScanResult


@dataclass(frozen=True)
class ScanFibonacciOpportunities:
    result_store: AnalysisResultStore

    def execute(
        self,
        levels: dict[str, Decimal],
        tolerance_percent: Decimal = Decimal("1"),
        limit: int = 20,
    ) -> FibonacciScanResult:
        if tolerance_percent < 0 or limit <= 0:
            raise ValueError("invalid fibonacci scan parameters")

        opportunities = []
        for raw_symbol, level in levels.items():
            symbol = raw_symbol.strip().upper()
            record = self.result_store.get_record(symbol)
            if record is None:
                continue
            entry = record.result.entry_context
            if entry.current_price is None:
                continue
            current = entry.current_price.value
            if level <= 0:
                continue
            distance = abs(current - level) / level * Decimal("100")
            if distance > tolerance_percent:
                continue
            score = record.result.stock_quality.total_score
            opportunities.append(
                FibonacciOpportunity(
                    symbol=symbol,
                    current_price=current,
                    level=level,
                    distance_percent=distance,
                    direction="near_retracement",
                    score=score,
                )
            )

        opportunities.sort(key=lambda x: (x.distance_percent, -x.score, x.symbol))
        return FibonacciScanResult(
            opportunities=tuple(opportunities[:limit]),
            metric="distance_to_fibonacci_level_percent",
            data_status="HISTORICAL_ANALYSIS_RESULT",
        )
