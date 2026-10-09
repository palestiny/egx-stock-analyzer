from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from uuid import UUID

from app.application.backtesting.historical_dataset_runner import HistoricalDatasetBacktestRunner
from app.domain.backtesting.simulator import BacktestConfiguration
from app.domain.stocks.stock import Stock
from app.infrastructure.historical_dataset.financial_source import HistoricalDatasetFundamentalSnapshotSource
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader
from app.infrastructure.historical_dataset.market_provider import HistoricalDatasetMarketDataProvider


FIXTURE = Path("tests/fixtures/historical_dataset/v1")
STOCK = Stock(UUID("00000000-0000-0000-0000-000000000001"), "TEST", "Test Stock")
CONFIG = BacktestConfiguration(
    max_holding_bars=3,
    transaction_cost_rate=Decimal("0"),
    slippage_rate=Decimal("0"),
)


def test_dataset_runner_executes_production_strategy_boundary_deterministically() -> None:
    loader = HistoricalDatasetLoader(FIXTURE)
    runner = HistoricalDatasetBacktestRunner(
        STOCK,
        HistoricalDatasetMarketDataProvider(loader),
        HistoricalDatasetFundamentalSnapshotSource(loader),
    )

    first = runner.run(date(2026, 2, 16), date(2026, 2, 27), CONFIG)
    second = runner.run(date(2026, 2, 16), date(2026, 2, 27), CONFIG)

    assert first == second
    assert first.strategy_id == "opportunity-classification"
    assert first.strategy_version == "0"
    assert first.configuration == CONFIG
    assert first.completed_trade_count == len(first.trades)


def test_dataset_runner_uses_pre_evaluation_bars_only_for_warmup() -> None:
    loader = HistoricalDatasetLoader(FIXTURE)
    runner = HistoricalDatasetBacktestRunner(
        STOCK,
        HistoricalDatasetMarketDataProvider(loader),
        HistoricalDatasetFundamentalSnapshotSource(loader),
    )

    result = runner.run(
        date(2026, 2, 16),
        date(2026, 2, 27),
        CONFIG,
        evaluation_start_date=date(2026, 2, 24),
    )

    assert result.configuration.warmup_bars == 6
    assert all(
        trade.signal_timestamp.astimezone().date() >= date(2026, 2, 24)
        for trade in result.trades
    )


def test_dataset_runner_rejects_evaluation_start_outside_loaded_window() -> None:
    loader = HistoricalDatasetLoader(FIXTURE)
    runner = HistoricalDatasetBacktestRunner(
        STOCK,
        HistoricalDatasetMarketDataProvider(loader),
        HistoricalDatasetFundamentalSnapshotSource(loader),
    )

    with pytest.raises(ValueError, match="evaluation_start_date"):
        runner.run(
            date(2026, 2, 16),
            date(2026, 2, 27),
            CONFIG,
            evaluation_start_date=date(2026, 2, 10),
        )
