from pathlib import Path

from tools.egx_stock_analyzer_m61_probe import probe_symbol


def test_probe_symbol_includes_deterministic_market_validation(monkeypatch, tmp_path: Path):
    payload = {
        "success": True,
        "data": {
            "exchange": "EGX",
            "ticker": "EGAL",
            "currency": "EGP",
            "price_unit": "major",
            "points": [
                {
                    "date": "2025-01-02",
                    "open": 100,
                    "high": 105,
                    "low": 99,
                    "close": 103,
                    "volume": 1000,
                },
                {
                    "date": "2025-01-03",
                    "open": 103,
                    "high": 104,
                    "low": 102,
                    "close": 103,
                    "volume": 1200,
                },
            ],
        },
        "meta": {
            "count": 2,
            "first_date": "2025-01-02",
            "last_date": "2025-01-03",
            "data_freshness": "daily",
        },
    }
    raw = b'{"success":true}'
    monkeypatch.setattr(
        "tools.egx_stock_analyzer_m61_probe.request_json",
        lambda path, params, api_key: (200, payload, raw),
    )

    result = probe_symbol("EGAL", "secret-test-key", False, tmp_path)

    assert result["status_code"] == 200
    assert result["observed"]["validation_findings"] == []
    assert result["raw_sha256"]
    assert not (tmp_path / "EGAL.json").exists()


def test_probe_symbol_reports_invalid_market_points(monkeypatch, tmp_path: Path):
    payload = {
        "success": True,
        "data": {
            "points": [
                {
                    "date": "2025-01-02",
                    "open": 100,
                    "high": 90,
                    "low": 99,
                    "close": 95,
                    "volume": -1,
                }
            ]
        },
        "meta": {},
    }
    monkeypatch.setattr(
        "tools.egx_stock_analyzer_m61_probe.request_json",
        lambda path, params, api_key: (200, payload, b"bad-market-data"),
    )

    result = probe_symbol("EGAL", "secret-test-key", False, tmp_path)

    findings = result["observed"]["validation_findings"]
    assert "row[0]:low_above_high" in findings
    assert "row[0]:low_above_ohlc" in findings
    assert "row[0]:high_below_ohlc" in findings
    assert "row[0]:negative_volume" in findings
