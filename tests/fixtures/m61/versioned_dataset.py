from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.application.backtesting.versioned_dataset import VersionedDatasetManifest
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.historical_financial_snapshot import (
    HistoricalFinancialSnapshot,
)
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


class RepositoryHistoricalDatasetFixture:
    """Test-only loader for the repository-owned M61 deterministic fixture.

    This JSON loader is deliberately confined to tests. It does not select the
    production historical artifact format defined by DEC-128.
    """

    def __init__(self, fixture_directory: Path) -> None:
        manifest_payload = json.loads(
            (fixture_directory / "manifest.json").read_text(encoding="utf-8")
        )
        self.manifest = VersionedDatasetManifest.from_dict(manifest_payload)

        artifact = (fixture_directory / "egx_strategy_v0.json").read_bytes()
        self.manifest.verify_integrity(artifact)
        self._payload = json.loads(artifact.decode("utf-8"))

    def get_daily_observations(
        self,
        stock: Stock | UUID,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        stock_id = stock.id if isinstance(stock, Stock) else stock
        if from_date > to_date:
            raise ValueError("from_date must not be after to_date")
        if not self.manifest.covers(from_date, to_date):
            raise ValueError("Requested range is outside fixture coverage")

        rows = [
            row
            for row in self._payload["market_observations"]
            if UUID(row["stock_id"]) == stock_id
            and from_date <= datetime.fromisoformat(row["timestamp"]).date() <= to_date
        ]
        rows.sort(key=lambda row: datetime.fromisoformat(row["timestamp"]))

        return [
            RawPriceBarObservation(
                stock_id=UUID(row["stock_id"]),
                timeframe=Timeframe.DAILY,
                timestamp=datetime.fromisoformat(row["timestamp"]),
                open=Decimal(row["open"]),
                high=Decimal(row["high"]),
                low=Decimal(row["low"]),
                close=Decimal(row["close"]),
                volume=int(row["volume"]),
            )
            for row in rows
        ]

    def get_snapshots(
        self,
        stock: Stock | UUID,
    ) -> list[HistoricalFinancialSnapshot]:
        stock_id = stock.id if isinstance(stock, Stock) else stock
        rows = [
            row
            for row in self._payload["financial_snapshots"]
            if UUID(row["stock_id"]) == stock_id
        ]
        rows.sort(
            key=lambda row: (
                date.fromisoformat(row["period_end"]),
                date.fromisoformat(row["available_at"]),
            )
        )

        return [
            HistoricalFinancialSnapshot(
                period=FinancialPeriod(
                    period_end=date.fromisoformat(row["period_end"]),
                    revenue=Decimal(row["revenue"]),
                    net_income=Decimal(row["net_income"]),
                    current_assets=Decimal(row["current_assets"])
                    if row["current_assets"] is not None
                    else None,
                    current_liabilities=Decimal(row["current_liabilities"])
                    if row["current_liabilities"] is not None
                    else None,
                ),
                available_at=date.fromisoformat(row["available_at"]),
            )
            for row in rows
        ]
