#!/usr/bin/env python3
"""One bounded, unauthenticated EGID history-access check; never stores price data."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

BASE_URL = "https://ticker.egidegypt.com"
HISTORY_PATH = "/api/DelayedFeed/getSymbolHistory"
MAX_RESPONSE_BYTES = 1_000_000


def _shape(value: object, path: str = "$") -> dict[str, object]:
    """Describe response shape without returning any field values."""
    if isinstance(value, dict):
        result: dict[str, object] = {"type": "object", "keys": sorted(str(k) for k in value)[:80]}
        arrays: dict[str, int] = {}
        for key, child in value.items():
            if isinstance(child, list):
                arrays[f"{path}.{key}"] = len(child)
            elif isinstance(child, dict):
                nested = _shape(child, f"{path}.{key}")
                nested_arrays = nested.get("array_lengths")
                if isinstance(nested_arrays, dict):
                    arrays.update(nested_arrays)
        result["array_lengths"] = arrays
        return result
    if isinstance(value, list):
        return {"type": "array", "length": len(value)}
    return {"type": type(value).__name__}


def probe_unauthenticated_history_access(timeout: float = 12.0) -> dict[str, Any]:
    """Request at most ten COMI daily rows, without credentials or persistence."""
    payload = {
        "FromDate": "2025-01-01T00:00:00",
        "ToDate": "2025-01-05T23:59:59",
        "SymbolCode": "COMI",
        "Skip": 0,
        "Take": 10,
    }
    request = urllib.request.Request(
        f"{BASE_URL}{HISTORY_PATH}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "egx-stock-analyzer-m61-egid-access-probe/1.0",
        },
        method="POST",
    )
    status_code = 0
    content_type: str | None = None
    raw = b""
    transport_error: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = response.status
            content_type = response.headers.get("Content-Type")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        content_type = exc.headers.get("Content-Type")
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        transport_error = type(exc).__name__

    too_large = len(raw) > MAX_RESPONSE_BYTES
    parsed: object | None = None
    json_valid = False
    if raw and not too_large:
        try:
            parsed = json.loads(raw)
            json_valid = True
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    if transport_error:
        classification = "UNVERIFIED_TRANSPORT_FAILURE"
    elif status_code in {401, 403}:
        classification = "AUTH_REQUIRED_OR_ACCESS_DENIED"
    elif status_code == 404:
        classification = "HISTORY_ENDPOINT_NOT_FOUND"
    elif 200 <= status_code < 300 and json_valid:
        classification = "UNAUTHENTICATED_ENDPOINT_RESPONDED"
    elif 200 <= status_code < 300:
        classification = "UNAUTHENTICATED_RESPONSE_NOT_JSON"
    else:
        classification = "REQUEST_REJECTED_OR_FAILED"

    report: dict[str, Any] = {
        "provider": "EGID",
        "endpoint": HISTORY_PATH,
        "request": {
            "symbol": "COMI",
            "from": payload["FromDate"],
            "to": payload["ToDate"],
            "maximum_rows_requested": payload["Take"],
            "authorization_header_sent": False,
        },
        "observed": {
            "classification": classification,
            "http_status": status_code,
            "content_type": content_type,
            "response_bytes": len(raw),
            "response_exceeded_size_limit": too_large,
            "response_is_json": json_valid,
            "response_shape": _shape(parsed) if json_valid else None,
            "transport_error_type": transport_error,
        },
        "created_at_utc": datetime.now(UTC).isoformat(),
        "price_values_persisted": False,
        "source_terms_verified": False,
        "long_term_storage_rights_verified": False,
        "dataset_accepted": False,
    }
    return report


def main() -> int:
    report = probe_unauthenticated_history_access()
    print(json.dumps(report, indent=2, sort_keys=True))
    classification = report["observed"]["classification"]
    return 2 if classification == "UNVERIFIED_TRANSPORT_FAILURE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
