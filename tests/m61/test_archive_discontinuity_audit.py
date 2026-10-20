import csv
import gzip
from pathlib import Path

import pytest

from tools.m61_archive_discontinuity_audit import audit


FIELDS = ["symbol", "session_date", "open", "high", "low", "close", "volume"]


def _write_csv(path: Path, rows: list[list[object]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        writer.writerows(rows)
    return path


def test_flags_large_close_move_and_overnight_gap_without_repairing_prices(tmp_path: Path) -> None:
    path = _write_csv(tmp_path / "prices.csv", [
        ["EGAL", "2026-01-01", 100, 105, 95, 100, 1000],
        ["EGAL", "2026-01-02", 100, 130, 99, 125, 1200],
        ["COMI", "2026-01-01", 50, 52, 49, 50, 900],
        ["COMI", "2026-01-02", 65, 66, 64, 65, 1100],
    ])

    result = audit(path)

    assert result["status"] == "completed"
    assert result["usable_unique_rows"] == 4
    assert result["flag_count"] == 2
    assert result["flags_by_symbol"] == {"COMI": 1, "EGAL": 1}
    egal_flag = next(flag for flag in result["flags"] if flag["symbol"] == "EGAL")
    assert egal_flag["close_to_close_change"] == 0.25
    assert egal_flag["close"] == 125
    assert "unchanged" in egal_flag["review_note"]


def test_skips_duplicate_and_malformed_rows_and_counts_them(tmp_path: Path) -> None:
    path = _write_csv(tmp_path / "prices.csv", [
        ["COMI", "2026-01-01", 50, 52, 49, 50, 900],
        ["COMI", "2026-01-01", 50, 52, 49, 50, 900],
        ["COMI", "not-a-date", 50, 52, 49, 50, 900],
    ])

    result = audit(path)

    assert result["input_rows"] == 3
    assert result["usable_unique_rows"] == 1
    assert result["duplicate_rows_skipped"] == 1
    assert result["rejected_rows"] == 1
    assert result["flag_count"] == 0


def test_reads_gzip_and_rejects_invalid_threshold(tmp_path: Path) -> None:
    plain = _write_csv(tmp_path / "prices.csv", [
        ["COMI", "2026-01-01", 50, 52, 49, 50, 900],
        ["COMI", "2026-01-02", 51, 52, 50, 51, 1000],
    ])
    gz_path = tmp_path / "prices.csv.gz"
    with plain.open("rb") as source, gzip.open(gz_path, "wb") as target:
        target.write(source.read())

    assert audit(gz_path)["usable_unique_rows"] == 2
    with pytest.raises(ValueError, match="threshold"):
        audit(gz_path, 0)
