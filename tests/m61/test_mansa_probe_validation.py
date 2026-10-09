from pathlib import Path

from tools.egx_stock_analyzer_m61_probe import probe_result_passes, probe_symbol


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

    findings = result["observed"]["validation_findings"]
    assert result["status_code"] == 200
    assert "m61:insufficient_warmup=0;required=252" in findings
    assert "m61:coverage_starts_after_requested=2025-01-02" in findings
    assert "m61:coverage_ends_before_evaluation_end=2025-01-03" in findings
    assert not any(item.startswith("row[") for item in findings)
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


def test_probe_preserves_exact_raw_response_for_checksum_evidence(monkeypatch, tmp_path: Path):
    raw = b'{"success":true,"data":{"points":[]}}'
    monkeypatch.setattr(
        "tools.egx_stock_analyzer_m61_probe.request_json",
        lambda path, params, api_key: (200, {"success": True, "data": {"points": []}}, raw),
    )

    result = probe_symbol("EGAL", "secret-test-key", True, tmp_path)

    artifact = tmp_path / "EGAL.json"
    assert artifact.read_bytes() == raw
    assert result["raw_sha256"]
    assert artifact.read_bytes() == raw


def test_m61_probe_requires_252_observations_before_evaluation_start(monkeypatch, tmp_path: Path):
    points = [
        {
            "date": "2020-12-31",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": 1000,
        },
        {
            "date": "2021-01-04",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": 1000,
        },
    ]
    monkeypatch.setattr(
        "tools.egx_stock_analyzer_m61_probe.request_json",
        lambda path, params, api_key: (
            200,
            {"success": True, "data": {"points": points}, "meta": {}},
            b"raw",
        ),
    )

    result = probe_symbol("EGAL", "secret-test-key", False, tmp_path)

    assert "m61:insufficient_warmup=1;required=252" in result["observed"]["validation_findings"]



def test_http_200_with_invalid_history_does_not_pass_evidence_gate(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "tools.egx_stock_analyzer_m61_probe.request_json",
        lambda path, params, api_key: (
            200,
            {"success": True, "data": {"points": []}, "meta": {"count": 0}},
            b'{"success":true,"data":{"points":[]}}',
        ),
    )

    result = probe_symbol("COMI", "secret-test-key", False, tmp_path)

    assert result["status_code"] == 200
    assert result["observed"]["validation_findings"]
    assert probe_result_passes(result) is False


def test_probe_rejects_response_without_data_object(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "tools.egx_stock_analyzer_m61_probe.request_json",
        lambda path, params, api_key: (200, {"success": True}, b'{"success":true}'),
    )

    result = probe_symbol("COMI", "secret-test-key", False, tmp_path)

    assert "response:data_not_object" in result["observed"]["validation_findings"]
    assert probe_result_passes(result) is False


def test_probe_rejects_provider_meta_count_mismatch(monkeypatch, tmp_path: Path):
    points = [
        {
            "date": "2025-01-02",
            "open": 10,
            "high": 11,
            "low": 9,
            "close": 10,
            "volume": 100,
        }
    ]
    monkeypatch.setattr(
        "tools.egx_stock_analyzer_m61_probe.request_json",
        lambda path, params, api_key: (
            200,
            {"success": True, "data": {"points": points}, "meta": {"count": 2}},
            b"raw",
        ),
    )

    result = probe_symbol("COMI", "secret-test-key", False, tmp_path)

    assert "response:meta_count_mismatch=2;actual=1" in result["observed"]["validation_findings"]
    assert probe_result_passes(result) is False
