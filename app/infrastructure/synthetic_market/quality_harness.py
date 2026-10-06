from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.fundamental_analysis.growth import RevenueGrowthAnalyzer
from app.domain.fundamental_analysis.historical_financial_snapshot import HistoricalFinancialSnapshot
from app.domain.fundamental_analysis.liquidity import CurrentRatioAnalyzer
from app.domain.fundamental_analysis.profitability import NetProfitMarginAnalyzer
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
from app.domain.fundamental_analysis.scoring import FundamentalScorer, FundamentalScore
from app.domain.scoring.stock_quality import StockQualityScore, StockQualityScorer
from app.domain.technical_analysis.scoring import TechnicalScore

from .research_scenarios import SyntheticResearchScenario, SyntheticFinancialSnapshot


@dataclass(frozen=True)
class SyntheticQualitySnapshot:
    symbol: str
    stock_id: UUID
    decision_date: date
    fundamental_score: int
    technical_score: int
    total_score: int
    current_period_end: date
    previous_period_end: date


@dataclass(frozen=True)
class SyntheticQualityReport:
    decision_date: date
    snapshots: tuple[SyntheticQualitySnapshot, ...]

    @property
    def average_total_score(self) -> Decimal:
        if not self.snapshots:
            return Decimal("0")
        return Decimal(sum(item.total_score for item in self.snapshots)) / Decimal(len(self.snapshots))


class SyntheticQualityHarness:
    """Exercises PIT fundamental analysis together with existing technical scoring."""

    def run(
        self,
        scenario: SyntheticResearchScenario,
        technical_snapshots: dict[UUID, TechnicalScore],
        *,
        decision_date: date,
    ) -> SyntheticQualityReport:
        by_stock: dict[UUID, list[SyntheticFinancialSnapshot]] = {}
        for snapshot in scenario.financial_snapshots:
            by_stock.setdefault(snapshot.stock_id, []).append(snapshot)

        series_by_stock = {series.stock_id: series for series in scenario.dataset.series}
        results: list[SyntheticQualitySnapshot] = []

        for stock_id, snapshots in by_stock.items():
            ordered = sorted(snapshots, key=lambda item: (item.period_end, item.available_at))
            available = [
                HistoricalFinancialSnapshot(
                    period=self._period(snapshot),
                    available_at=snapshot.available_at.date(),
                )
                for snapshot in ordered
                if snapshot.available_at.date() <= decision_date
            ]
            if len(available) < 2:
                continue

            current = max(available, key=lambda item: item.period.period_end)
            previous_candidates = [
                item for item in available
                if item.period.period_end < current.period.period_end
            ]
            if not previous_candidates:
                continue
            previous = max(previous_candidates, key=lambda item: item.period.period_end)

            analysis = FundamentalAnalysisResult(
                stock_id=stock_id,
                period_end=current.period.period_end,
                profitability=NetProfitMarginAnalyzer.analyze(current.period),
                liquidity=CurrentRatioAnalyzer.analyze(current.period),
                growth=RevenueGrowthAnalyzer.analyze(current.period, previous.period),
            )
            fundamental: FundamentalScore = FundamentalScorer.score(analysis)
            technical = technical_snapshots.get(
                stock_id,
                TechnicalScore(0, 0, 0, 0),
            )
            quality: StockQualityScore = StockQualityScorer.score(fundamental, technical)
            results.append(
                SyntheticQualitySnapshot(
                    symbol=series_by_stock[stock_id].symbol,
                    stock_id=stock_id,
                    decision_date=decision_date,
                    fundamental_score=fundamental.total,
                    technical_score=technical.total_score,
                    total_score=quality.total_score,
                    current_period_end=current.period.period_end,
                    previous_period_end=previous.period.period_end,
                )
            )

        return SyntheticQualityReport(
            decision_date=decision_date,
            snapshots=tuple(results),
        )

    @staticmethod
    def _period(snapshot: SyntheticFinancialSnapshot):
        from app.domain.fundamental_analysis.financial_period import FinancialPeriod

        return FinancialPeriod(
            period_end=snapshot.period_end,
            revenue=snapshot.revenue,
            net_income=snapshot.net_income,
            current_assets=snapshot.current_assets,
            current_liabilities=snapshot.current_liabilities,
        )
