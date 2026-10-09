import json

from tools.m61_egid_history_access_probe import inspect_response


def test_access_denied_is_not_treated_as_dataset():
    report = inspect_response(401, "application/json", b'{"error":"unauthorized"}')
    assert report["status"] == "AUTH_REQUIRED_OR_ACCESS_DENIED"
    assert report["credentials_supplied"] is False
    assert report["dataset_accepted"] is False


def test_success_reports_field_names_and_dates_without_price_values():
    payload = {"data": [
        {"Date": "2020-12-30", "Open": 10, "High": 11, "Low": 9, "Close": 10, "Volume": 100},
        {"Date": "2021-01-03", "Open": 10, "High": 12, "Low": 9, "Close": 11, "Volume": 120},
    ]}
    report = inspect_response(200, "application/json", json.dumps(payload).encode())
    assert report["status"] == "HTTP_SUCCESS_CANDIDATE_ONLY"
    assert report["row_count"] == 2
    assert report["first_date"] == "2020-12-30"
    assert report["last_date"] == "2021-01-03"
    assert "Open" not in json.dumps(report)
    assert report["dataset_accepted"] is False


def test_success_with_unknown_shape_is_not_guessed():
    report = inspect_response(200, "application/json", b'{"message":"ok","data":[]}')
    assert report["status"] == "HTTP_SUCCESS_SCHEMA_UNRESOLVED"
