from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from tools.m61_yahoo_acquisition import normalize_history_rows, write_market_artifact


def test_normalize_history_rows_is_deterministic() -> None:
    stock_id = UUID("00000000-0000-0000-0000-000000000001")
    rows = [
        {
            "Date": datetime(2021, 1, 4, tzinfo=UTC),
            "Open": 10.0,
            "High": 11.0,
            "Low": 9.5,
            "Close": 10.5,
            "Volume": 123,
        },
        {
            "Date": datetime(2021, 1, 5, tzinfo=UTC),
            "Open": 10.5,
            "High": 11.2,
            "Low": 10.1,
            "Close": 11.0,
            "Volume": 456,
        },
    ]

    normalized = normalize_history_rows(rows, stock_id)

    assert normalized == [
        {
            "stock_id": str(stock_id),
            "timeframe": "1d",
            "timestamp": "2021-01-04T00:00:00+00:00",
            "open": Decimal("10.0"),
            "high": Decimal("11.0"),
            "low": Decimal("9.5"),
            "close": Decimal("10.5"),
            "volume": Decimal("123"),
            "source": "Yahoo Finance / yfinance",
        },
        {
            "stock_id": str(stock_id),
            "timeframe": "1d",
            "timestamp": "2021-01-05T00:00:00+00:00",
            "open": Decimal("10.5"),
            "high": Decimal("11.2"),
            "low": Decimal("10.1"),
            "close": Decimal("11.0"),
            "volume": Decimal("456"),
            "source": "Yahoo Finance / yfinance",
        },
    ]


def test_write_market_artifact_writes_m61_columns(tmp_path: Path) -> None:
    stock_id = UUID("00000000-0000-0000-0000-000000000001")
    rows = normalize_history_rows(
        [
            {
                "Date": datetime(2021, 1, 4, tzinfo=UTC),
                "Open": 10.0,
                "High": 11.0,
                "Low": 9.5,
                "Close": 10.5,
                "Volume": 123,
            }
        ],
        stock_id,
    )

    path = write_market_artifact(rows, tmp_path / "market_observations.csv")

    with path.open(newline="", encoding="utf-8") as handle:
        data = list(csv.DictReader(handle))

    assert data[0]["stock_id"] == str(stock_id)
    assert data[0]["timeframe"] == "1d"
    assert data[0]["timestamp"] == "2021-01-04T00:00:00+00:00"
    assert data[0]["volume"] == "123"
