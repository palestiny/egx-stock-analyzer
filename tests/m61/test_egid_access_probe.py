from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from email.message import Message

from tools import m61_egid_access_probe as probe


class _FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, limit=-1):
        return b'{"Data":[{"SymbolCode":"COMI","Close":123.45},{"SymbolCode":"COMI","Close":124.00}]}'


def test_probe_reports_response_shape_without_exposing_price_values(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(probe.urllib.request, "urlopen", fake_urlopen)
    report = probe.probe_unauthenticated_history_access()

    assert report["observed"]["http_status"] == 200
    assert report["observed"]["classification"] == "UNAUTHENTICATED_ENDPOINT_RESPONDED"
    assert report["observed"]["response_shape"]["keys"] == ["Data"]
    assert report["observed"]["response_shape"]["array_lengths"]["$.Data"] == 2
    assert "123.45" not in json.dumps(report)
    assert report["price_values_persisted"] is False
    request = captured["request"]
    assert request.get_header("Authorization") is None
    payload = json.loads(request.data)
    assert payload["SymbolCode"] == "COMI"
    assert payload["Take"] == 10
    assert captured["timeout"] == 12.0


def test_probe_classifies_unauthorized_access_without_returning_error_body(monkeypatch):
    headers = Message()
    headers["Content-Type"] = "application/json"

    def unauthorized(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", headers, BytesIO(b'{"error":"auth required"}')
        )

    monkeypatch.setattr(probe.urllib.request, "urlopen", unauthorized)
    report = probe.probe_unauthenticated_history_access()

    assert report["observed"]["http_status"] == 401
    assert report["observed"]["classification"] == "AUTH_REQUIRED_OR_ACCESS_DENIED"
    assert report["observed"]["response_shape"]["keys"] == ["error"]
    assert "auth required" not in json.dumps(report)
    assert report["dataset_accepted"] is False


def test_probe_classifies_transport_failure_without_credentials(monkeypatch):
    def unavailable(request, timeout):
        raise urllib.error.URLError("network unavailable")

    monkeypatch.setattr(probe.urllib.request, "urlopen", unavailable)
    report = probe.probe_unauthenticated_history_access()

    assert report["observed"]["classification"] == "UNVERIFIED_TRANSPORT_FAILURE"
    assert report["observed"]["transport_error_type"] == "URLError"



def test_probe_allows_only_the_two_documented_history_routes():
    try:
        probe.probe_unauthenticated_history_access(history_path="/api/Settings/GetToken")
    except ValueError as exc:
        assert "allowlisted endpoints" in str(exc)
    else:
        raise AssertionError("non-history paths must not be probed")


def test_probe_can_check_the_documented_feed_history_route_without_credentials(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        return _FakeResponse()

    monkeypatch.setattr(probe.urllib.request, "urlopen", fake_urlopen)
    report = probe.probe_unauthenticated_history_access(
        history_path="/api/Feed/GetSymbolHistory"
    )

    assert report["endpoint"] == "/api/Feed/GetSymbolHistory"
    assert report["observed"]["classification"] == "UNAUTHENTICATED_ENDPOINT_RESPONDED"
    assert captured["request"].full_url.endswith("/api/Feed/GetSymbolHistory")
    assert captured["request"].get_header("Authorization") is None
    assert "123.45" not in json.dumps(report)
    assert report["dataset_accepted"] is False
