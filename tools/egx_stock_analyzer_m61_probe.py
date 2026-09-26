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
from datetime import UTC, datetime
from pathlib import Path

from tools.m61_market_validation import validate_history_points

COHORT = ("COMI", "EGAL", "SWDY", "ETEL", "EAST", "TMGH", "PHDC", "FWRY", "EFID", "HRHO")
BASE_URL = "https://mansaapi.com"
FROM_DATE = "2020-01-01"
TO_DATE = "2025-12-31"


def build_url(path: str, params: dict[str, str]) -> str:
    return f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"


def request_json(path: str, params: dict[str, str], api_key: str) -> tuple[int, dict, bytes]:
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
            return response.status, json.loads(body), body
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw_error": body.decode("utf-8", errors="replace")}
        return exc.code, payload, body


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
    points = data.get("points", []) if isinstance(data, dict) else []
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}

    if isinstance(data, dict):
        result["observed"].update(
            {
                "exchange": data.get("exchange"),
                "ticker": data.get("ticker"),
                "currency": data.get("currency"),
                "price_unit": data.get("price_unit"),
                "point_count": len(points) if isinstance(points, list) else None,
                "first_date": meta.get("first_date"),
                "last_date": meta.get("last_date"),
                "meta_count": meta.get("count"),
                "data_freshness": meta.get("data_freshness"),
                "validation_findings": validate_history_points(points)
                if isinstance(points, list)
                else ["points:not_list"],
            }
        )
    result["raw_sha256"] = hashlib.sha256(raw_body).hexdigest()
    if status != 200:
        result["error"] = payload

    if preserve_raw:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{symbol}.json").write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        result["raw_artifact"] = str(output_dir / f"{symbol}.json")

    return result


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

    return 0 if all(r["status_code"] == 200 for r in run["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
