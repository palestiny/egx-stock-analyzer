from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.research.dataset import PriceAdjustment, ResearchBar


@dataclass(frozen=True)
class ResearchDataset:
    """An immutable, explicitly versioned OHLCV series for reproducible research."""

    symbol: str
    timeframe: str
    provider: str
    version: str
    adjustment: PriceAdjustment
    bars: tuple[ResearchBar, ...]

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (self.symbol, self.timeframe, self.provider, self.version)):
            raise ValueError("research dataset identity fields are required")


class ResearchDatasetRepository(Protocol):
    """Application port; implementations must return the exact requested dataset identity."""

    def get(
        self,
        *,
        symbol: str,
        timeframe: str,
        provider: str,
        version: str,
        adjustment: PriceAdjustment,
    ) -> ResearchDataset | None:
        ...


class InMemoryResearchDatasetRepository:
    """Small deterministic adapter for tests and local research; not durable storage."""

    def __init__(self, datasets: tuple[ResearchDataset, ...] = ()) -> None:
        self._datasets: dict[tuple[str, str, str, str, PriceAdjustment], ResearchDataset] = {}
        for dataset in datasets:
            key = self._key(
                dataset.symbol, dataset.timeframe, dataset.provider,
                dataset.version, dataset.adjustment,
            )
            if key in self._datasets:
                raise ValueError("duplicate research dataset identity")
            self._datasets[key] = dataset

    def get(
        self,
        *,
        symbol: str,
        timeframe: str,
        provider: str,
        version: str,
        adjustment: PriceAdjustment,
    ) -> ResearchDataset | None:
        return self._datasets.get(self._key(symbol, timeframe, provider, version, adjustment))

    @staticmethod
    def _key(
        symbol: str,
        timeframe: str,
        provider: str,
        version: str,
        adjustment: PriceAdjustment,
    ) -> tuple[str, str, str, str, PriceAdjustment]:
        return symbol, timeframe, provider, version, adjustment
