import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tools.egx_daily_history_audit import EXPECTED_COLUMNS


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def write_clean_csv(path: Path, **overrides: str) -> None:
    row = {
        "session_date": "2026-11-10",
        "instrument_type": "equity",
        "symbol": "COMI",
        "price_unit": "EGP",
        "open_value": "100",
        "high_value": "110",
        "low_value": "95",
        "close_value": "105",
        "volume_thousands_reported": "12.5",
        "change_pct_reported": "-1.25",
        "traded_value_egp": "",
        "executions_count": "",
        "source_name": "Example provider",
        "source_url": "https://example.com/history",
        "retrieved_at": "2026-11-10T19:16:35+02:00",
        "price_type": "daily historical OHLCV",
        "delay_status": "historical table; exact quote latency not stated",
        "quality_status": "source_reported",
        "notes": "Fixture for CLI smoke test.",
    }
    row.update(overrides)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerow(row)


def run_cli(input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.egx_daily_history_audit",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_cli_writes_json_report_and_returns_zero_for_clean_fixture(tmp_path: Path) -> None:
    archive = tmp_path / "clean.csv"
    report_path = tmp_path / "reports" / "audit.json"
    write_clean_csv(archive)
    original_bytes = archive.read_bytes()

    result = run_cli(archive, report_path)

    assert result.returncode == 0, result.stderr
    stdout_report = json.loads(result.stdout)
    file_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert stdout_report == file_report
    assert stdout_report["status"] == "clean"
    assert stdout_report["artifact"]["byte_count"] == len(original_bytes)
    assert stdout_report["artifact"]["sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert archive.read_bytes() == original_bytes


def test_cli_audits_repository_archive_without_modifying_it(tmp_path: Path) -> None:
    archive = REPOSITORY_ROOT / "data" / "market_history" / "egx_daily_history.csv"
    report_path = tmp_path / "egx-daily-history-audit.json"
    original_bytes = archive.read_bytes()

    result = run_cli(archive, report_path)

    assert result.returncode == 1, result.stderr
    stdout_report = json.loads(result.stdout)
    file_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert stdout_report == file_report
    assert stdout_report["status"] == "completed_with_findings"
    assert stdout_report["row_count"] == stdout_report["parsed_row_count"]
    assert stdout_report["malformed_row_count"] == 0
    assert stdout_report["unlabelled_ohlc_inconsistency_count"] == 0
    assert stdout_report["artifact"]["byte_count"] == len(original_bytes)
    assert stdout_report["artifact"]["sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert archive.read_bytes() == original_bytes


def test_cli_reports_unlabelled_ohlc_findings_and_returns_one(tmp_path: Path) -> None:
    archive = tmp_path / "review.csv"
    report_path = tmp_path / "audit.json"
    write_clean_csv(archive, open_value="99", low_value="100")
    original_bytes = archive.read_bytes()

    result = run_cli(archive, report_path)

    assert result.returncode == 1, result.stderr
    stdout_report = json.loads(result.stdout)
    file_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert stdout_report == file_report
    assert stdout_report["status"] == "completed_with_findings"
    assert stdout_report["unlabelled_ohlc_inconsistency_count"] == 1
    assert archive.read_bytes() == original_bytes
