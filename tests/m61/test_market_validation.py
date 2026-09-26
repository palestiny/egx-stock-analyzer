from tools.m61_market_validation import validate_history_points


def test_valid_points_have_no_findings():
    points = [
        {"date": "2025-01-02", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 100},
        {"date": "2025-01-05", "open": 11, "high": 13, "low": 10, "close": 12, "volume": 120},
    ]
    assert validate_history_points(points) == []


def test_validator_detects_duplicates_and_ordering():
    points = [
        {"date": "2025-01-03", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 100},
        {"date": "2025-01-03", "open": 11, "high": 13, "low": 10, "close": 12, "volume": 120},
        {"date": "2025-01-02", "open": 11, "high": 13, "low": 10, "close": 12, "volume": 120},
    ]
    findings = validate_history_points(points)
    assert "row[1]:duplicate_date=2025-01-03" in findings
    assert "row[2]:out_of_order=2025-01-02" in findings


def test_validator_detects_ohlcv_integrity_errors():
    points = [
        {"date": "2025-01-02", "open": 12, "high": 8, "low": 9, "close": 11, "volume": -1},
    ]
    findings = validate_history_points(points)
    assert "row[0]:low_above_high" in findings
    assert "row[0]:low_above_ohlc" in findings
    assert "row[0]:high_below_ohlc" in findings
    assert "row[0]:negative_volume" in findings


def test_validator_reports_missing_and_invalid_fields():
    findings = validate_history_points([{"date": "bad", "open": "x"}])
    assert "row[0]:missing=high,low,close,volume" in findings
    assert "row[0]:invalid_date=bad" in findings
