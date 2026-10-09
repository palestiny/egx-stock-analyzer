#!/usr/bin/env python3
"""M61 Mansa Markets acquisition probe.

This is acquisition tooling, not a production MarketDataProvider.
It never writes API keys to output. Raw responses are only persisted when
--preserve-raw is explicitly supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

from tools.m61_market_validation import validate_history_points, validate_m61_evaluation_window

COHORT = ("COMI", "EGAL", "SWDY", "ETEL", "EAST", "TMGH", "PHDC", "FWRY", "EFID", "HRHO")
BASE_URL = "https://mansaapi.com"
FROM_DATE = "2019-01-01"
TO_DATE = "2025-12-31"


def build_url(path: str, params: dict[str, str]) -> str:
    return f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"


def request_json(path: str, params: dict[str, str], api_key: str) -> tuple[int, object, bytes]:
    request = urllib.request.Request(
        build_url(path, params),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "egx-stock-analyzer-m61-probe/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            try:
                payload = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = {"error": "invalid_json_response"}
            return response.status, payload, body
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"error": "http_error_response_not_json"}
        return exc.code, payload, body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # Keep acquisition failures in the machine-readable run report rather than
        # terminating midway with an unstructured traceback.
        message = "request_timeout" if isinstance(exc, TimeoutError) else "request_failed"
        return 0, {"error": message, "error_type": type(exc).__name__}, b""


def probe_symbol(symbol: str, api_key: str, preserve_raw: bool, output_dir: Path) -> dict:
    path = f"/api/v1/markets/exchanges/EGX/stocks/{urllib.parse.quote(symbol, safe='')}/history"
    params = {"from": FROM_DATE, "to": TO_DATE, "order": "asc", "limit": "20000"}
    status, payload, raw_body = request_json(path, params, api_key)

    result = {
        "symbol": symbol,
        "status_code": status,
        "requested": {"from": FROM_DATE, "to": TO_DATE, "order": "asc", "limit": 20000},
        "observed": {},
    }

    data = payload.get("data") if isinstance(payload, dict) else None
    raw_meta = payload.get("meta") if isinstance(payload, dict) else None
    meta = raw_meta if isinstance(raw_meta, dict) else {}
    findings: list[str] = []

    if not isinstance(payload, dict):
        findings.append("response:not_object")
    elif payload.get("success") is False:
        findings.append("response:provider_reported_failure")
    if not isinstance(payload, dict) or payload.get("success") is not True:
        findings.append("response:success_flag_not_true")
    if not isinstance(raw_meta, dict):
        findings.append("response:meta_not_object")
    if not isinstance(data, dict):
        findings.append("response:data_not_object")
        points = None
    else:
        expected_identity = {
            "exchange": "EGX",
            "ticker": symbol.strip().upper(),
            "currency": "EGP",
        }
        for field, expected in expected_identity.items():
            actual = data.get(field)
            if not isinstance(actual, str) or not actual.strip():
                findings.append(f"response:missing_identity={field}")
            elif actual.strip().upper() != expected:
                findings.append(
                    f"response:identity_mismatch={field};expected={expected};actual={actual.strip()}"
                )
        if not isinstance(data.get("price_unit"), str) or not data["price_unit"].strip():
            findings.append("response:missing_identity=price_unit")

        points = data.get("points")
        if not isinstance(points, list):
            findings.append("response:points_not_list")
        else:
            findings.extend(validate_history_points(points))
            findings.extend(validate_m61_evaluation_window(points))
            if not points:
                findings.append("response:empty_history")
            if "count" not in meta or meta.get("count") is None:
                findings.append("response:meta_count_missing")
            else:
                reported_count = meta["count"]
                if isinstance(reported_count, bool) or not isinstance(reported_count, int):
                    findings.append("response:meta_count_invalid")
                elif reported_count != len(points):
                    findings.append(
                        f"response:meta_count_mismatch={reported_count};actual={len(points)}"
                    )
            if points:
                actual_first = str(points[0].get("date", "")).strip()
                actual_last = str(points[-1].get("date", "")).strip()
                for field, actual in (("first_date", actual_first), ("last_date", actual_last)):
                    reported = meta.get(field)
                    if not isinstance(reported, str) or not reported.strip():
                        findings.append(f"response:meta_{field}_missing")
                    else:
                        try:
                            reported_date = date.fromisoformat(reported.strip())
                            actual_date = date.fromisoformat(actual)
                        except ValueError:
                            findings.append(f"response:meta_{field}_invalid")
                        else:
                            if reported_date != actual_date:
                                findings.append(
                                    f"response:meta_{field}_mismatch={reported_date.isoformat()};actual={actual_date.isoformat()}"
                                )
        result["observed"].update(
            {
                "exchange": data.get("exchange"),
                "ticker": data.get("ticker"),
                "currency": data.get("currency"),
                "price_unit": data.get("price_unit"),
                "point_count": len(points) if isinstance(points, list) else None,
                "first_date": meta.get("first_date") if isinstance(meta, dict) else None,
                "last_date": meta.get("last_date") if isinstance(meta, dict) else None,
                "meta_count": meta.get("count") if isinstance(meta, dict) else None,
                "data_freshness": meta.get("data_freshness") if isinstance(meta, dict) else None,
            }
        )
    result["observed"]["validation_findings"] = findings
    result["raw_sha256"] = hashlib.sha256(raw_body).hexdigest()
    if status != 200:
        result["error"] = payload

    if preserve_raw:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{symbol}.json").write_bytes(raw_body)
        result["raw_artifact"] = str(output_dir / f"{symbol}.json")

    return result


def probe_result_passes(result: dict) -> bool:
    """A successful HTTP status is insufficient unless the evidence passes validation."""
    return (
        result.get("status_code") == 200
        and not result.get("observed", {}).get("validation_findings", ["validation_missing"])
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Mansa EGX historical OHLCV for M61.")
    parser.add_argument("--api-key-env", default="MANSA_API_KEY")
    parser.add_argument("--output-dir", type=Path, default=Path("m61-mansa-probe-output"))
    parser.add_argument("--preserve-raw", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        print(f"Missing API key environment variable: {args.api_key_env}", file=sys.stderr)
        return 2

    run = {
        "provider": "Mansa Markets",
        "exchange": "EGX",
        "cohort": list(COHORT),
        "window": {"from": FROM_DATE, "to": TO_DATE},
        "requested_at": datetime.now(UTC).isoformat(),
        "raw_preserved": args.preserve_raw,
        "results": [],
    }

    for symbol in COHORT:
        result = probe_symbol(symbol, api_key, args.preserve_raw, args.output_dir)
        run["results"].append(result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))

    if args.preserve_raw:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "run.json").write_text(
            json.dumps(run, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    return 0 if all(probe_result_passes(result) for result in run["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
