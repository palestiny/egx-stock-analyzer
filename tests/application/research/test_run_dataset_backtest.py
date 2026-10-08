from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.application.research.dataset_repository import (
    InMemoryResearchDatasetRepository,
    ResearchDataset,
)
from app.application.research.run_dataset_backtest import (
    DatasetBacktestRequest,
    ResearchDatasetIdentityError,
    ResearchDatasetNotFoundError,
    RunDatasetBacktest,
)
from app.application.research.backtest import BacktestStatus
from app.domain.research.dataset import (
    PriceAdjustment,
    ResearchBar,
    ResearchCostConfig,
    ResearchRunConfig,
)


def make_bar(day: int, *, symbol="COMI", timeframe="1d", provider="fixture", version="v1"):
    timestamp = datetime(2026, 10, day, tzinfo=timezone.utc)
    return ResearchBar(
        symbol, timeframe, timestamp, timestamp,
        Decimal("100"), Decimal("105"), Decimal("95"), Decimal("100"),
        Decimal("1000"), provider, version,
        adjustment=PriceAdjustment.UNADJUSTED,
    )


def make_config(*, provider="fixture", version="v1"):
    return ResearchRunConfig(
        dataset_version=version,
        provider=provider,
        strategy_id="test",
        strategy_version="1",
        evaluator_version="1",
        adjustment=PriceAdjustment.UNADJUSTED,
        costs=ResearchCostConfig(Decimal("0"), Decimal("0")),
    )


def make_dataset(*, bars=None):
    return ResearchDataset(
        symbol="COMI",
        timeframe="1d",
        provider="fixture",
        version="v1",
        adjustment=PriceAdjustment.UNADJUSTED,
        bars=tuple(bars if bars is not None else (make_bar(1), make_bar(2))),
    )


def test_exact_dataset_identity_runs_and_is_reproducible():
    use_case = RunDatasetBacktest(InMemoryResearchDatasetRepository((make_dataset(),)))
    request = DatasetBacktestRequest("COMI", "1d", make_config())
    first = use_case.execute(request, lambda history: None)
    second = use_case.execute(request, lambda history: None)
    assert first.status is BacktestStatus.COMPLETED
    assert first.run_id == second.run_id


def test_missing_exact_dataset_version_is_not_silently_substituted():
    use_case = RunDatasetBacktest(InMemoryResearchDatasetRepository((make_dataset(),)))
    with pytest.raises(ResearchDatasetNotFoundError):
        use_case.execute(
            DatasetBacktestRequest("COMI", "1d", make_config(version="v2")),
            lambda history: None,
        )


def test_wrong_symbol_or_timeframe_does_not_match_dataset():
    use_case = RunDatasetBacktest(InMemoryResearchDatasetRepository((make_dataset(),)))
    with pytest.raises(ResearchDatasetNotFoundError):
        use_case.execute(
            DatasetBacktestRequest("EGAL", "1d", make_config()),
            lambda history: None,
        )


def test_dataset_with_mixed_bar_identity_fails_before_strategy_runs():
    dataset = make_dataset(bars=(make_bar(1), make_bar(2, symbol="EGAL")))
    use_case = RunDatasetBacktest(InMemoryResearchDatasetRepository((dataset,)))
    called = False

    def strategy(history):
        nonlocal called
        called = True
        return None

    with pytest.raises(ResearchDatasetIdentityError):
        use_case.execute(DatasetBacktestRequest("COMI", "1d", make_config()), strategy)
    assert not called


def test_invalid_quality_is_reported_by_engine_not_hidden_by_repository():
    bars = (make_bar(1),)
    dataset = make_dataset(bars=bars)
    use_case = RunDatasetBacktest(InMemoryResearchDatasetRepository((dataset,)))
    result = use_case.execute(DatasetBacktestRequest("COMI", "1d", make_config()), lambda history: None)
    assert result.status is BacktestStatus.COMPLETED


def test_duplicate_dataset_identity_is_rejected():
    with pytest.raises(ValueError, match="duplicate research dataset identity"):
        InMemoryResearchDatasetRepository((make_dataset(), make_dataset()))
