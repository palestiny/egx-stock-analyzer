from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from tools import m61_free_market_probe as probe


def _payload():
    dates = [
        int(datetime(2020, 12, 30, tzinfo=UTC).timestamp()),
        int(datetime(2021, 1, 3, tzinfo=UTC).timestamp()),
    ]
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": "COMI.CA",
                        "exchangeTimezoneName": "Africa/Cairo",
                        "currency": "EGP",
                        "fullExchangeName": "Egyptian Exchange",
                        "instrumentType": "EQUITY",
                    },
                    "timestamp": dates,
                    "indicators": {
                        "quote": [{
                            "open": [10.0, 11.0],
                            "high": [12.0, 13.0],
                            "low": [9.0, 10.0],
                            "close": [11.0, 12.0],
                            "volume": [1000, 1200],
                        }],
                        "adjclose": [{"adjclose": [10.5, 11.5]}],
                    },
                    "events": {
                        "dividends": {"event-1": {"date": dates[1], "amount": 0.5}},
                        "splits": {},
                    },
                }
            ],
            "error": None,
        }
    }


def test_build_url_uses_bounded_daily_request_and_fixed_ticker_allowlist():
    url = probe.build_url("COMI.CA")
    assert "interval=1d" in url
    assert "events=div%2Csplits" in url
    assert "period1=" in url and "period2=" in url
    try:
        probe.build_url("NOT-ALLOWED")
    except ValueError as exc:
        assert "fixed M61 exploratory cohort" in str(exc)
    else:
        raise AssertionError("arbitrary ticker should be rejected")


def test_parse_chart_keeps_source_and_adjusted_close_separate():
    points, meta, findings = probe._parse_chart("COMI.CA", _payload())
    assert meta["exchange_timezone"] == "Africa/Cairo"
    assert len(points) == 2
    assert points[0]["close"] == 11.0
    assert points[0]["adj_close"] == 10.5
    assert points[1]["dividend"] == 0.5
    assert not any(item.startswith("response:") for item in findings)


def test_parse_chart_fails_closed_when_timezone_is_missing():
    payload = _payload()
    del payload["chart"]["result"][0]["meta"]["exchangeTimezoneName"]
    points, _, findings = probe._parse_chart("COMI.CA", payload)
    assert points == []
    assert "response:missing_exchange_timezone" in findings


def test_parse_chart_rejects_ticker_mismatch_without_returning_rows():
    payload = _payload()
    payload["chart"]["result"][0]["meta"]["symbol"] = "EGAL.CA"
    points, _, findings = probe._parse_chart("COMI.CA", payload)
    assert points == []
    assert any(item.startswith("response:ticker_mismatch=") for item in findings)


def test_parse_chart_excludes_rows_outside_requested_date_range():
    payload = _payload()
    payload["chart"]["result"][0]["timestamp"][0] = int(
        datetime(2018, 12, 31, tzinfo=UTC).timestamp()
    )
    points, _, findings = probe._parse_chart("COMI.CA", payload)
    assert len(points) == 1
    assert points[0]["date"] == "2021-01-03"
    assert "row[0]:date_outside_requested_range=2018-12-31" in findings


def test_parse_chart_skips_non_finite_timestamps():
    payload = _payload()
    payload["chart"]["result"][0]["timestamp"][0] = float("nan")
    points, _, findings = probe._parse_chart("COMI.CA", payload)
    assert len(points) == 1
    assert "row[0]:invalid_timestamp" in findings


def test_probe_saves_raw_bytes_and_candidate_csv_only_when_requested(monkeypatch, tmp_path: Path):
    raw = json.dumps(_payload(), separators=(",", ":")).encode()
    monkeypatch.setattr(
        probe,
        "request_chart",
        lambda ticker: (200, _payload(), raw),
    )
    result = probe.probe_ticker("COMI", "COMI.CA", True, tmp_path)
    artifact = tmp_path / "COMI.yahoo-chart.raw.json"
    candidate_csv = tmp_path / "COMI.market-candidate.csv"
    assert artifact.read_bytes() == raw
    assert candidate_csv.exists()
    assert result["observed"]["sha256_of_response"] == __import__("hashlib").sha256(raw).hexdigest()
    assert result["acceptance"]["status"] == "CANDIDATE_ONLY"
    assert result["acceptance"]["eligible_for_strategy_v0"] is False


def test_probe_does_not_persist_response_without_explicit_opt_in(monkeypatch, tmp_path: Path):
    raw = json.dumps(_payload(), separators=(",", ":")).encode()
    monkeypatch.setattr(probe, "request_chart", lambda ticker: (200, _payload(), raw))
    result = probe.probe_ticker("COMI", "COMI.CA", False, tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert result["observed"]["sha256_of_response"]


def test_probe_rejects_overwriting_nonempty_evidence_directory(monkeypatch, tmp_path: Path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "prior.txt").write_text("keep", encoding="utf-8")
    # The CLI checks this before any network request.
    monkeypatch.setattr(probe, "request_chart", lambda ticker: (_ for _ in ()).throw(AssertionError()))
    try:
        probe.main(["--output-dir", str(output), "--symbols", "COMI"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("CLI must refuse to overwrite an evidence directory")


def test_parse_chart_fails_closed_on_wrong_market_timezone_or_currency():
    payload = _payload()
    payload["chart"]["result"][0]["meta"]["exchangeTimezoneName"] = "America/New_York"
    points, _, findings = probe._parse_chart("COMI.CA", payload)
    assert points == []
    assert "response:unexpected_exchange_timezone='America/New_York'" in findings

    payload = _payload()
    payload["chart"]["result"][0]["meta"]["currency"] = "USD"
    points, _, findings = probe._parse_chart("COMI.CA", payload)
    assert points == []
    assert "response:unexpected_currency='USD'" in findings
