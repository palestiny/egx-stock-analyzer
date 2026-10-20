from __future__ import annotations

import csv
import gzip
from datetime import date, timedelta
from pathlib import Path

from tools.m61_archive_technical_diagnostic import (
    Bar,
    analyze_bars,
    read_bars,
)


def _bars(count: int = 35) -> list[Bar]:
    start = date(2022, 1, 2)
    rows = []
    for index in range(count):
        close = 20.0 + index * 0.1
        volume = 200.0 if index == 22 else 100.0
        rows.append(
            Bar(
                symbol="COMI",
                session_date=start + timedelta(days=index),
                open=close - 0.05,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=volume,
            )
        )
    return rows


def test_archive_diagnostic_reports_realistic_technical_groups() -> None:
    bars = _bars()
    summary = {"input_rows": len(bars), "usable_rows": len(bars)}
    report = analyze_bars(bars, summary)

    assert report["analysis_type"] == "exploratory_technical_forward_return_diagnostic"
    pooled = report["pooled_forward_returns"]
    assert pooled["baseline"]["1"]["samples"] > 0
    assert pooled["positive_momentum_5d"]["5"]["samples"] > 0
    assert pooled["momentum_volume_1_5x"]["1"]["samples"] > 0
    assert pooled["pre_breakout_proxy"]["1"]["samples"] > 0
    assert report["per_symbol"]["COMI"]["rows"] == len(bars)
    assert report["limitations"]


def test_reader_skips_invalid_ohlc_and_duplicate_symbol_date(tmp_path: Path) -> None:
    path = tmp_path / "prices.csv.gz"
    headers = [
        "symbol", "session_date", "open", "high", "low", "close", "volume",
    ]
    valid = ["COMI", "2022-01-02", "10", "11", "9", "10.5", "100"]
    invalid = ["COMI", "2022-01-03", "10", "9", "8", "10.5", "100"]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerow(valid)
        writer.writerow(valid)
        writer.writerow(invalid)

    bars, summary = read_bars(path)

    assert len(bars) == 1
    assert summary["input_rows"] == 3
    assert summary["usable_rows"] == 1
    assert summary["duplicate_symbol_date_rows_skipped"] == 1
    assert summary["invalid_ohlc_rows"] == 1


def test_invalid_first_duplicate_does_not_suppress_later_valid_bar(tmp_path: Path) -> None:
    path = tmp_path / "prices.csv"
    headers = [
        "symbol", "session_date", "open", "high", "low", "close", "volume",
    ]
    invalid = ["COMI", "2022-01-02", "10", "9", "8", "10.5", "100"]
    valid = ["COMI", "2022-01-02", "10", "11", "9", "10.5", "100"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerow(invalid)
        writer.writerow(valid)

    bars, summary = read_bars(path)

    assert len(bars) == 1
    assert bars[0].close == 10.5
    assert summary["invalid_ohlc_rows"] == 1
    assert summary["duplicate_symbol_date_rows_skipped"] == 0
    assert summary["usable_rows"] == 1
