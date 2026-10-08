from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.application.research.backtest import BacktestResult, Strategy, run_backtest
from app.application.research.dataset_repository import ResearchDatasetRepository
from app.domain.research.dataset import PriceAdjustment, ResearchRunConfig


class ResearchDatasetNotFoundError(LookupError):
    """The exact requested dataset version is not available."""


class ResearchDatasetIdentityError(ValueError):
    """Loaded dataset contents do not match the requested research identity."""


@dataclass(frozen=True)
class DatasetBacktestRequest:
    symbol: str
    timeframe: str
    config: ResearchRunConfig
    initial_capital: Decimal = Decimal("100000")
    parameters_json: str = "{}"

    def __post_init__(self) -> None:
        if not self.symbol.strip() or not self.timeframe.strip():
            raise ValueError("symbol and timeframe are required")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")


class RunDatasetBacktest:
    """Resolve an exact dataset identity, validate its series, then delegate replay."""

    def __init__(self, datasets: ResearchDatasetRepository) -> None:
        self._datasets = datasets

    def execute(self, request: DatasetBacktestRequest, strategy: Strategy) -> BacktestResult:
        dataset = self._datasets.get(
            symbol=request.symbol,
            timeframe=request.timeframe,
            provider=request.config.provider,
            version=request.config.dataset_version,
            adjustment=request.config.adjustment,
        )
        if dataset is None:
            raise ResearchDatasetNotFoundError(
                "No research dataset matches symbol, timeframe, provider, version, and adjustment"
            )

        for bar in dataset.bars:
            if (
                bar.symbol != request.symbol
                or bar.timeframe != request.timeframe
                or bar.provider != request.config.provider
                or bar.dataset_version != request.config.dataset_version
                or bar.adjustment is not request.config.adjustment
            ):
                raise ResearchDatasetIdentityError(
                    "research dataset contains bars outside the requested dataset identity"
                )

        return run_backtest(
            dataset.bars,
            config=request.config,
            strategy=strategy,
            initial_capital=request.initial_capital,
            parameters_json=request.parameters_json,
        )
