from tools.m61_market_validation import validate_history_points, validate_m61_evaluation_window


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
        {"date": "2025-01-02", "open": 12, "high": 8, "low": 13, "close": 11, "volume": -1},
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


def test_validator_preserves_decimal_precision_without_float_coercion():
    points = [
        {
            "date": "2025-01-02",
            "open": "0.1000000000000000001",
            "high": "0.1000000000000000002",
            "low": "0.1000000000000000000",
            "close": "0.10000000000000000015",
            "volume": "100",
        },
    ]
    assert validate_history_points(points) == []


def test_validator_rejects_non_finite_decimal_values():
    points = [
        {
            "date": "2025-01-02",
            "open": "NaN",
            "high": "Infinity",
            "low": "0.1",
            "close": "0.1",
            "volume": "100",
        },
    ]
    findings = validate_history_points(points)
    assert "row[0]:non_finite_open=NaN" in findings
    assert "row[0]:non_finite_high=Infinity" in findings


def test_duplicate_rows_do_not_inflate_m61_warmup_count():
    points = [
        {
            "date": "2020-01-02",
            "open": 10,
            "high": 11,
            "low": 9,
            "close": 10,
            "volume": 100,
        }
        for _ in range(252)
    ]

    findings = validate_m61_evaluation_window(points)

    assert "m61:insufficient_warmup=1;required=252" in findings



def test_validator_rejects_non_positive_prices():
    points = [
        {
            "date": "2025-01-02",
            "open": 0,
            "high": 1,
            "low": -1,
            "close": 0.5,
            "volume": 100,
        },
    ]

    findings = validate_history_points(points)

    assert "row[0]:non_positive_open=0" in findings
    assert "row[0]:non_positive_low=-1" in findings
