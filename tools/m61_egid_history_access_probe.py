"""Single unauthenticated EGID history access probe; never logs or saves prices."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def request_history() -> tuple[int, str, bytes]:
    body = json.dumps({
        "SymbolCode": "COMI",
        "FromDate": "2019-01-01T00:00:00",
        "ToDate": "2026-01-01T00:00:00",
        "Skip": 0,
        "Take": 10000,
    }).encode()
    request = urllib.request.Request(
        "https://ticker.egidegypt.com/api/Feed/GetSymbolHistory",
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "User-Agent": "egx-stock-analyzer-m61-egid-access-probe/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, "", json.dumps({"error_type": type(exc).__name__}).encode()


def _key(value: object) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def _row_candidates(value: Any) -> list[list[dict[str, Any]]]:
    found: list[list[dict[str, Any]]] = []
    if isinstance(value, dict):
        for child in value.values():
            found.extend(_row_candidates(child))
    elif isinstance(value, list):
        rows = [item for item in value if isinstance(item, dict)]
        if rows:
            keys = {_key(k) for k in rows[0]}
            if keys & {"date", "datetime", "timestamp", "tradingdate"} and {"open", "high", "low", "close"} <= keys:
                found.append(rows)
            for row in rows:
                found.extend(_row_candidates(row))
    return found


def inspect_response(status: int, content_type: str, raw: bytes) -> dict[str, Any]:
    report: dict[str, Any] = {
        "provider": "EGID public feed",
        "endpoint": "/api/Feed/GetSymbolHistory",
        "symbol": "COMI",
        "credentials_supplied": False,
        "price_values_logged": False,
        "http_status": status,
        "content_type": content_type,
        "response_bytes": len(raw),
        "response_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "row_count": 0,
        "row_field_names": [],
        "first_date": None,
        "last_date": None,
        "dataset_accepted": False,
    }
    if status in {401, 403}:
        report["status"] = "AUTH_REQUIRED_OR_ACCESS_DENIED"
        return report
    if status != 200:
        report["status"] = "REQUEST_FAILED"
        return report
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        report["status"] = "NON_JSON_RESPONSE"
        return report
    report["top_level_keys"] = sorted(str(k) for k in payload) if isinstance(payload, dict) else []
    candidates = _row_candidates(payload)
    if not candidates:
        report["status"] = "HTTP_SUCCESS_SCHEMA_UNRESOLVED"
        return report
    rows = max(candidates, key=len)
    report["status"] = "HTTP_SUCCESS_CANDIDATE_ONLY"
    report["row_count"] = len(rows)
    report["row_field_names"] = sorted(str(k) for k in rows[0])
    normalized_dates = []
    for row in rows:
        normalized = {_key(k): v for k, v in row.items()}
        value = next((normalized[k] for k in ("date", "datetime", "timestamp", "tradingdate") if k in normalized), None)
        if isinstance(value, str) and len(value) >= 10:
            normalized_dates.append(value[:10])
    report["first_date"] = min(normalized_dates) if normalized_dates else None
    report["last_date"] = max(normalized_dates) if normalized_dates else None
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    status, content_type, raw = request_history()
    report = inspect_response(status, content_type, raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "http_status", "row_count", "dataset_accepted") if k in report}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
