from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.market_intelligence.stress import (
    CrashRadarAnalyzer,
    CrashRadarSignal,
    MarketStressAnalyzer,
    MarketStressSnapshot,
)
from .generator import SyntheticDataset


@dataclass(frozen=True)
class SyntheticStressReport:
    scenario_name: str
    seed: int
    stock_signals: tuple[CrashRadarSignal, ...]
    market: MarketStressSnapshot


class SyntheticStressHarness:
    """Runs crash and market-stress logic over the complete synthetic cohort."""

    def run(self, dataset: SyntheticDataset, *, lookback: int = 20) -> SyntheticStressReport:
        signals = tuple(
            CrashRadarAnalyzer.analyze(
                series.stock_id,
                list(series.bars),
                lookback=lookback,
            )
            for series in dataset.series
        )
        return SyntheticStressReport(
            scenario_name=dataset.scenario.name,
            seed=dataset.scenario.seed,
            stock_signals=signals,
            market=MarketStressAnalyzer.analyze(list(signals)),
        )
