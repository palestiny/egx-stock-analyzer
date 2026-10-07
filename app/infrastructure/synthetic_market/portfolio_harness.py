from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.portfolio.construction import (
    PortfolioConfiguration,
    PortfolioEvaluation,
    PortfolioEvaluator,
    PortfolioPosition,
)

from .generator import SyntheticDataset


@dataclass(frozen=True)
class SyntheticPortfolioReport:
    scenario_name: str
    seed: int
    positions: tuple[PortfolioPosition, ...]
    invested_weight: Decimal
    cash_weight: Decimal
    metrics: object


class SyntheticPortfolioHarness:
    """Runs portfolio construction over synthetic cohort returns only."""

    def __init__(self, *, max_single_name_weight: Decimal = Decimal("0.20")) -> None:
        self._configuration = PortfolioConfiguration(
            max_single_name_weight=max_single_name_weight
        )

    def run(self, dataset: SyntheticDataset) -> SyntheticPortfolioReport:
        if not dataset.series:
            raise ValueError("synthetic dataset cannot be empty")

        equal_weight = Decimal("1") / Decimal(len(dataset.series))
        weight = min(equal_weight, self._configuration.max_single_name_weight)
        positions = [
            PortfolioPosition(symbol=series.symbol, weight=weight)
            for series in dataset.series
        ]

        returns_by_symbol: dict[str, list[Decimal]] = {}
        for series in dataset.series:
            closes = [bar.close.value for bar in series.bars]
            returns_by_symbol[series.symbol] = [
                (closes[index] - closes[index - 1]) / closes[index - 1]
                for index in range(1, len(closes))
            ]

        evaluation: PortfolioEvaluation = PortfolioEvaluator.evaluate_series(
            positions,
            configuration=self._configuration,
            returns_by_symbol=returns_by_symbol,
        )
        return SyntheticPortfolioReport(
            scenario_name=dataset.scenario.name,
            seed=dataset.scenario.seed,
            positions=evaluation.positions,
            invested_weight=evaluation.snapshot.invested_weight,
            cash_weight=evaluation.snapshot.cash_weight,
            metrics=evaluation.metrics,
        )
