from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.application.backtesting.historical_dataset_runner import HistoricalDatasetBacktestRunner
from app.domain.backtesting.simulator import BacktestConfiguration
from app.domain.stocks.stock import Stock
from app.infrastructure.historical_dataset.loader import HistoricalDatasetLoader


FIXTURE = Path("tests/fixtures/historical_dataset/v1")
STOCK = Stock(UUID("00000000-0000-0000-0000-000000000001"), "TEST", "Test Stock")
CONFIG = BacktestConfiguration(
    max_holding_bars=3,
    transaction_cost_rate=Decimal("0"),
    slippage_rate=Decimal("0"),
)


def test_dataset_runner_executes_production_strategy_boundary_deterministically() -> None:
    runner = HistoricalDatasetBacktestRunner(STOCK, HistoricalDatasetLoader(FIXTURE))

    first = runner.run(date(2026, 2, 16), date(2026, 2, 27), CONFIG)
    second = runner.run(date(2026, 2, 16), date(2026, 2, 27), CONFIG)

    assert first == second
    assert first.strategy_id == "opportunity-classification"
    assert first.strategy_version == "0"
    assert first.configuration == CONFIG
    assert first.completed_trade_count == len(first.trades)
