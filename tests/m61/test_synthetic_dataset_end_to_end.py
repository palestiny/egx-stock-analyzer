from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.application.backtesting.historical_dataset_runner import (
    HistoricalDatasetBacktestRunner,
)
from app.domain.backtesting.simulator import BacktestConfiguration
from app.domain.stocks.stock import Stock
from app.infrastructure.historical_dataset.financial_source import (
    HistoricalDatasetFundamentalSnapshotSource,
)
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader
from app.infrastructure.historical_dataset.market_provider import (
    HistoricalDatasetMarketDataProvider,
)
from tools.m61_generate_test_dataset import build_test_dataset


def test_generated_dataset_runs_production_strategy_end_to_end_deterministically(
    tmp_path: Path,
) -> None:
    dataset_dir = tmp_path / "m61-synthetic"
    summary = build_test_dataset(
        dataset_dir,
        date(2019, 1, 1),
        date(2021, 12, 31),
    )

    assert summary["symbols"] == 10
    assert summary["market_rows"] > 7_000
    assert summary["financial_rows"] == 80

    loader = HistoricalDatasetLoader(dataset_dir)
    manifest = loader.load_manifest()
    market = loader.load_market_observations()
    financial = loader.load_financial_snapshots()
    assert len(market) == summary["market_rows"]
    assert len(financial) == summary["financial_rows"]

    provenance = manifest.market_observations.provenance
    assert provenance is not None
    mappings = [
        mapping for mapping in provenance.symbol_mappings
        if mapping.split("->", maxsplit=1)[0].strip().upper() == "COMI"
    ]
    assert len(mappings) == 1
    stock_id = UUID(mappings[0].split("->", maxsplit=1)[1].strip())
    stock = Stock(stock_id, "COMI", "Commercial International Bank")

    runner = HistoricalDatasetBacktestRunner(
        stock,
        HistoricalDatasetMarketDataProvider(loader),
        HistoricalDatasetFundamentalSnapshotSource(loader),
    )
    configuration = BacktestConfiguration(
        max_holding_bars=10,
        transaction_cost_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.001"),
    )

    first = runner.run(
        date(2019, 1, 1),
        date(2021, 12, 31),
        configuration,
        evaluation_start_date=date(2021, 1, 1),
    )
    second = runner.run(
        date(2019, 1, 1),
        date(2021, 12, 31),
        configuration,
        evaluation_start_date=date(2021, 1, 1),
    )

    assert first == second
    assert first.strategy_id == "opportunity-classification"
    assert first.strategy_version == "0"
    assert first.configuration.warmup_bars >= 252
    assert first.completed_trade_count == len(first.trades)
    assert all(
        trade.signal_timestamp.date() >= date(2021, 1, 1)
        for trade in first.trades
    )
