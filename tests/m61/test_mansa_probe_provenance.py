from hashlib import sha256

from tools.egx_stock_analyzer_m61_probe import request_json


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b'{"success":true,"data":{"points":[]}}'


def test_request_json_returns_raw_bytes_for_provenance(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: FakeResponse(),
    )

    status, payload, raw = request_json(
        "/api/v1/markets/exchanges/EGX/stocks/EGAL/history",
        {"from": "2020-01-01", "to": "2025-12-31"},
        "test-key",
    )

    assert status == 200
    assert payload["success"] is True
    assert sha256(raw).hexdigest() == sha256(b'{"success":true,"data":{"points":[]}}').hexdigest()


def test_request_json_does_not_expose_api_key_in_payload(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: FakeResponse(),
    )

    _, payload, _ = request_json(
        "/history",
        {},
        "secret-test-key",
    )

    assert "secret-test-key" not in repr(payload)
