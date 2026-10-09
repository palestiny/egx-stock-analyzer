#!/usr/bin/env python3
"""Inspect the public EGID/EGX Swagger contract without downloading market prices.

This is a source-contract probe only. It does not call market-history operations,
authenticate, preserve price rows, or claim any historical data is licensed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SWAGGER_URL = "https://ticker.egidegypt.com/swagger/v1/swagger.json"
TARGETS = (
    ("POST", "/api/Feed/GetSymbolsChartByDateRange"),
    ("POST", "/api/Feed/GetAllSymbolsChartByDateRange"),
    ("POST", "/api/Feed/GetSymbolHistory"),
    ("GET", "/api/Feed/GetSymbolHistories"),
    ("POST", "/api/DelayedFeed/getSymbolHistory"),
)


def fetch_swagger() -> tuple[int, bytes]:
    request = urllib.request.Request(
        SWAGGER_URL,
        headers={"Accept": "application/json", "User-Agent": "egx-stock-analyzer-m61-egi-probe/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, json.dumps({"error": type(exc).__name__}).encode()


def _resolve_ref(ref: str, schemas: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    prefix = "#/components/schemas/"
    if not ref.startswith(prefix):
        return ref, None
    name = ref[len(prefix):]
    schema = schemas.get(name)
    return name, schema if isinstance(schema, dict) else None


def _schema_summary(schema: Any, schemas: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """Summarize field names/types only; never dump large provider schemas into CI logs."""
    if not isinstance(schema, dict):
        return {"schema_type": "unknown"}
    if depth >= 2:
        return {"schema_type": schema.get("type", "object"), "truncated": True}

    ref = schema.get("$ref")
    if isinstance(ref, str):
        name, resolved = _resolve_ref(ref, schemas)
        result: dict[str, Any] = {"$ref": name}
        if resolved is not None:
            result["definition"] = _schema_summary(resolved, schemas, depth + 1)
        return result

    result: dict[str, Any] = {
        key: schema[key]
        for key in ("type", "format", "description", "enum", "required")
        if key in schema and isinstance(schema[key], (str, int, float, list))
    }
    properties = schema.get("properties")
    if isinstance(properties, dict):
        names = sorted(properties)
        result["properties"] = {
            str(name): _property_summary(properties[name], schemas)
            for name in names[:60]
        }
        if len(names) > 60:
            result["properties_truncated"] = len(names) - 60
    items = schema.get("items")
    if isinstance(items, dict):
        result["items"] = _property_summary(items, schemas)
    return result


def _property_summary(schema: Any, schemas: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {"type": "unknown"}
    result: dict[str, Any] = {}
    for key in ("type", "format", "description", "enum"):
        value = schema.get(key)
        if isinstance(value, (str, int, float, list)):
            result[key] = value
    ref = schema.get("$ref")
    if isinstance(ref, str):
        name, _ = _resolve_ref(ref, schemas)
        result["$ref"] = name
    items = schema.get("items")
    if isinstance(items, dict):
        result["items"] = {
            key: items[key]
            for key in ("type", "format", "$ref")
            if key in items and isinstance(items[key], (str, int, float))
        }
    return result


def inspect_swagger(payload: Any, status_code: int, raw: bytes) -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "CONTRACT_DISCOVERY_ONLY",
        "source": "EGID public Swagger",
        "swagger_url": SWAGGER_URL,
        "http_status": status_code,
        "response_bytes": len(raw),
        "response_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
        "inspected_at_utc": datetime.now(UTC).isoformat(),
        "operations": [],
        "limitations": [
            "No market-history operation was invoked.",
            "Endpoint documentation does not prove historical depth, response quality, or data rights.",
            "No market data or financial statements were acquired.",
        ],
    }
    if status_code != 200:
        report["status"] = "UNAVAILABLE"
        report["error"] = "swagger_request_failed"
        return report
    if not isinstance(payload, dict):
        report["status"] = "INVALID_SWAGGER"
        report["error"] = "swagger_root_not_object"
        return report

    schemas_raw = payload.get("components", {}).get("schemas", {}) if isinstance(payload.get("components"), dict) else {}
    schemas = schemas_raw if isinstance(schemas_raw, dict) else {}
    paths = payload.get("paths")
    if not isinstance(paths, dict):
        report["status"] = "INVALID_SWAGGER"
        report["error"] = "paths_not_object"
        return report

    for method, path in TARGETS:
        path_item = paths.get(path)
        operation = path_item.get(method.lower()) if isinstance(path_item, dict) else None
        item: dict[str, Any] = {"method": method, "path": path, "found": isinstance(operation, dict)}
        if isinstance(operation, dict):
            item["operation_id"] = operation.get("operationId")
            item["summary"] = operation.get("summary")
            item["parameters"] = []
            parameters = operation.get("parameters")
            if isinstance(parameters, list):
                for parameter in parameters:
                    if isinstance(parameter, dict):
                        item["parameters"].append({
                            "name": parameter.get("name"),
                            "in": parameter.get("in"),
                            "required": parameter.get("required", False),
                            "schema": _schema_summary(parameter.get("schema"), schemas),
                        })
            request_body = operation.get("requestBody")
            if isinstance(request_body, dict):
                content = request_body.get("content")
                item["request_body"] = {}
                if isinstance(content, dict):
                    for media_type, media in content.items():
                        if isinstance(media, dict):
                            item["request_body"][media_type] = _schema_summary(media.get("schema"), schemas)
            responses = operation.get("responses")
            item["responses"] = {}
            if isinstance(responses, dict):
                for code, response in responses.items():
                    if not isinstance(response, dict):
                        continue
                    response_item: dict[str, Any] = {"description": response.get("description")}
                    content = response.get("content")
                    if isinstance(content, dict):
                        response_item["content"] = {}
                        for media_type, media in content.items():
                            if isinstance(media, dict):
                                response_item["content"][media_type] = _schema_summary(media.get("schema"), schemas)
                    item["responses"][str(code)] = response_item
        report["operations"].append(item)

    report["found_target_operations"] = sum(1 for item in report["operations"] if item["found"])
    report["status"] = "CONTRACT_FOUND" if report["found_target_operations"] else "TARGET_OPERATIONS_NOT_FOUND"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    status_code, raw = fetch_swagger()
    try:
        payload = json.loads(raw) if raw else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = None
    report = inspect_swagger(payload, status_code, raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "report": str(args.output),
        "status": report["status"],
        "http_status": status_code,
        "found_target_operations": report.get("found_target_operations", 0),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
