from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import AnalysisResultStore
from app.application.analysis.stock_analysis import StockAnalysisPipeline
from app.application.performance.baseline import PerformanceSample, measure
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.stocks.stock import Stock


STOCK_ID = UUID("00000000-0000-0000-0000-000000000001")


@dataclass(frozen=True)
class _StubResult:
    technical_score: SimpleNamespace
    fundamental_score: SimpleNamespace
    stock_quality: SimpleNamespace
    entry_quality: SimpleNamespace
    opportunity: SimpleNamespace


class _DeterministicStore:
    def __init__(self) -> None:
        self._result = _StubResult(
            technical_score=SimpleNamespace(total_score=70),
            fundamental_score=SimpleNamespace(total=65),
            stock_quality=SimpleNamespace(total_score=68),
            entry_quality=SimpleNamespace(total_score=72),
            opportunity=SimpleNamespace(classification=SimpleNamespace(value="WATCH")),
        )

    def get(self, symbol: str, owner_user_id=None):
        if symbol != "COMI":
            return None
        return self._result

    def get_record(self, symbol: str, owner_user_id=None):
        return None

    def get_snapshot(self, snapshot_id, owner_user_id=None):
        return None

    def get_history_by_analysis_run(self, analysis_run_id, owner_user_id=None):
        return ()

    def get_history(self, symbol: str, start_date=None, end_date=None, owner_user_id=None):
        return ()


def _environment() -> dict[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "repository_commit": commit,
    }


def _sample_payload(sample: PerformanceSample) -> dict[str, object]:
    return {
        "repetitions": sample.repetitions,
        "warmup_runs": sample.warmup_runs,
        "durations_seconds": list(sample.durations_seconds),
        "p50_seconds": sample.p50_seconds,
        "p95_seconds": sample.p95_seconds,
        "p99_seconds": sample.p99_seconds,
        "operations_per_second": sample.operations_per_second,
    }


def _price_bars() -> list[PriceBar]:
    bars: list[PriceBar] = []
    closes = [10, 12, 11, 14, 13, 16, 15, 18, 17, 20, 19, 22, 21, 24, 23, 26]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    for index, close in enumerate(closes):
        bars.append(
            PriceBar.create(
                stock_id=STOCK_ID,
                timeframe=Timeframe.DAILY,
                timestamp=start + timedelta(days=index),
                open=Price(Decimal(str(close - 1))),
                high=Price(Decimal(str(close + 1))),
                low=Price(Decimal(str(close - 1))),
                close=Price(Decimal(str(close))),
                volume=Volume(1000 + index * 100),
            )
        )
    return bars


def _financial_periods() -> tuple[FinancialPeriod, FinancialPeriod]:
    return (
        FinancialPeriod(
            period_end=date(2026, 6, 30),
            revenue=Decimal("1200000"),
            net_income=Decimal("180000"),
            current_assets=Decimal("900000"),
            current_liabilities=Decimal("600000"),
        ),
        FinancialPeriod(
            period_end=date(2025, 6, 30),
            revenue=Decimal("1000000"),
            net_income=Decimal("140000"),
            current_assets=Decimal("800000"),
            current_liabilities=Decimal("650000"),
        ),
    )


def main() -> None:
    store: AnalysisResultStore = _DeterministicStore()
    app = create_app(store)
    client = TestClient(app)

    response = client.get("/api/v1/analysis/COMI")
    response.raise_for_status()

    sample = measure(
        lambda: client.get("/api/v1/analysis/COMI").raise_for_status(),
        repetitions=10,
        warmup_runs=2,
    )

    payload = {
        "protocol": "PERFORMANCE_BASELINE_PROTOCOL",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "workload": {
            "id": "api.analysis_read.deterministic",
            "method": "GET",
            "path": "/api/v1/analysis/COMI",
            "external_network": False,
            "provider_calls": False,
            "repetitions": sample.repetitions,
            "warmup_runs": sample.warmup_runs,
        },
        "environment": _environment(),
        "result": _sample_payload(sample),
    }

    stock = Stock(
        symbol="COMI",
        name="Commercial International Bank",
        id=STOCK_ID,
    )
    history = GetAnalysisHistory(InMemoryStockCatalog([stock]), store)
    history_sample = measure(
        lambda: history.execute("COMI"),
        repetitions=10,
        warmup_runs=2,
    )

    history_payload = {
        "protocol": "PERFORMANCE_BASELINE_PROTOCOL",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "workload": {
            "id": "application.analysis_history.deterministic",
            "method": "APPLICATION",
            "operation": "GetAnalysisHistory.execute",
            "symbol": "COMI",
            "external_network": False,
            "provider_calls": False,
            "repetitions": history_sample.repetitions,
            "warmup_runs": history_sample.warmup_runs,
        },
        "environment": _environment(),
        "result": _sample_payload(history_sample),
    }

    bars = _price_bars()
    current_period, previous_period = _financial_periods()
    analysis_sample = measure(
        lambda: StockAnalysisPipeline.analyze(
            stock_id=STOCK_ID,
            timeframe=Timeframe.DAILY,
            price_bars=bars,
            current_period=current_period,
            previous_period=previous_period,
            momentum_lookback=5,
            volume_lookback=5,
        ),
        repetitions=10,
        warmup_runs=2,
    )

    analysis_payload = {
        "protocol": "PERFORMANCE_BASELINE_PROTOCOL",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "workload": {
            "id": "application.stock_analysis.deterministic",
            "method": "APPLICATION",
            "operation": "StockAnalysisPipeline.analyze",
            "symbol": "COMI",
            "timeframe": Timeframe.DAILY.value,
            "price_bar_count": len(bars),
            "momentum_lookback": 5,
            "volume_lookback": 5,
            "external_network": False,
            "provider_calls": False,
            "repetitions": analysis_sample.repetitions,
            "warmup_runs": analysis_sample.warmup_runs,
        },
        "environment": _environment(),
        "result": _sample_payload(analysis_sample),
    }

    output_dir = Path("artifacts/performance")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "api-analysis-read-baseline.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "application-analysis-history-baseline.json").write_text(
        json.dumps(history_payload, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "application-stock-analysis-baseline.json").write_text(
        json.dumps(analysis_payload, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps(analysis_payload, indent=2))


if __name__ == "__main__":
    main()
