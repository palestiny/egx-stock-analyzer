#!/usr/bin/env python3
"""Inspect EGID's public OpenAPI contract without requesting market data.

This diagnostic does not authenticate, call market-data operations, or download
historical prices. It records only endpoint/schema metadata needed to design a
bounded, no-cost access probe after the provider contract is understood.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

OPENAPI_URL = "https://ticker.egidegypt.com/swagger/v1/swagger.json"
MAX_SPEC_BYTES = 5_000_000
INTERESTING = re.compile(r"history|histories|chartbydate|symbols?chart|token", re.IGNORECASE)


def fetch_openapi(url: str = OPENAPI_URL, timeout: float = 15.0) -> dict[str, Any]:
    """Fetch and validate the public OpenAPI document with bounded response size."""
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "egx-stock-analyzer-m61-egid-contract-probe/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"OpenAPI request returned HTTP {response.status}")
            raw = response.read(MAX_SPEC_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not retrieve EGID OpenAPI document: {type(exc).__name__}") from exc

    if len(raw) > MAX_SPEC_BYTES:
        raise RuntimeError(f"OpenAPI document exceeds {MAX_SPEC_BYTES} bytes")
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("EGID OpenAPI response is not valid JSON") from exc
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        raise RuntimeError("EGID OpenAPI document is missing the paths object")
    if not (document.get("openapi") or document.get("swagger")):
        raise RuntimeError("EGID response does not declare an OpenAPI/Swagger version")
    return document


def _schema_summary(schema: object) -> dict[str, object] | None:
    if not isinstance(schema, dict):
        return None
    summary: dict[str, object] = {}
    for key in ("$ref", "type", "format", "items", "enum"):
        if key in schema:
            value = schema[key]
            if key == "items" and isinstance(value, dict):
                summary[key] = {k: value[k] for k in ("$ref", "type") if k in value}
            elif key == "enum" and isinstance(value, list):
                summary[key] = value[:20]
            else:
                summary[key] = value
    properties = schema.get("properties")
    if isinstance(properties, dict):
        summary["properties"] = {
            str(name): _schema_summary(value)
            for name, value in list(properties.items())[:80]
        }
    required = schema.get("required")
    if isinstance(required, list):
        summary["required"] = required
    return summary or None


def summarize_openapi(document: dict[str, Any]) -> dict[str, object]:
    """Return only history/chart/token contract metadata; omit response examples/data."""
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("OpenAPI document is missing paths")
    components = document.get("components")
    components = components if isinstance(components, dict) else {}
    schemas = components.get("schemas", document.get("definitions"))
    schemas = schemas if isinstance(schemas, dict) else {}
    security_schemes = components.get("securitySchemes", document.get("securityDefinitions"))
    security_schemes = security_schemes if isinstance(security_schemes, dict) else {}

    selected: list[dict[str, object]] = []
    for path, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        for method, operation in sorted(path_item.items()):
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId", ""))
            summary = str(operation.get("summary", ""))
            if not INTERESTING.search(f"{path} {operation_id} {summary}"):
                continue

            parameters: list[dict[str, object]] = []
            raw_parameters = operation.get("parameters", [])
            if isinstance(raw_parameters, list):
                for parameter in raw_parameters:
                    if not isinstance(parameter, dict):
                        continue
                    parameters.append({
                        "name": parameter.get("name"),
                        "in": parameter.get("in"),
                        "required": parameter.get("required", False),
                        "schema": _schema_summary(parameter.get("schema")),
                    })

            request_body: dict[str, object] | None = None
            body = operation.get("requestBody")
            if isinstance(body, dict):
                body_content = body.get("content")
                media_summaries: dict[str, object] = {}
                if isinstance(body_content, dict):
                    for media_type, media in body_content.items():
                        if isinstance(media, dict):
                            media_summaries[str(media_type)] = _schema_summary(media.get("schema"))
                request_body = {
                    "required": body.get("required", False),
                    "content": media_summaries,
                }

            responses = operation.get("responses")
            response_codes = sorted(str(code) for code in responses) if isinstance(responses, dict) else []
            response_schemas: dict[str, object] = {}
            if isinstance(responses, dict):
                for response_code, response in responses.items():
                    if not isinstance(response, dict):
                        continue
                    media_schemas: dict[str, object] = {}
                    response_content = response.get("content")
                    if isinstance(response_content, dict):
                        for media_type, media in response_content.items():
                            if isinstance(media, dict):
                                summary_schema = _schema_summary(media.get("schema"))
                                if summary_schema is not None:
                                    media_schemas[str(media_type)] = summary_schema
                    legacy_schema = _schema_summary(response.get("schema"))
                    if legacy_schema is not None:
                        media_schemas["default"] = legacy_schema
                    if media_schemas:
                        response_schemas[str(response_code)] = media_schemas
            selected.append({
                "path": path,
                "method": method.upper(),
                "operation_id": operation.get("operationId"),
                "summary": operation.get("summary"),
                "security": operation.get("security", document.get("security", [])),
                "parameters": parameters,
                "request_body": request_body,
                "response_codes": response_codes,
                "response_schemas": response_schemas,
            })

    referenced_schema_names: set[str] = set()

    def collect_schema_refs(value: object) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str):
                prefix = "#/components/schemas/" if "#/components/schemas/" in ref else "#/definitions/"
                if prefix in ref:
                    referenced_schema_names.add(ref.rsplit("/", 1)[-1])
            for child in value.values():
                collect_schema_refs(child)
        elif isinstance(value, list):
            for child in value:
                collect_schema_refs(child)

    collect_schema_refs(selected)
    schema_summaries: dict[str, object] = {}
    for name, schema in sorted(schemas.items()):
        if (
            re.search(r"history|symbolchart|token|authentication", str(name), re.IGNORECASE)
            or str(name) in referenced_schema_names
        ):
            schema_summaries[str(name)] = _schema_summary(schema)

    servers = document.get("servers")
    server_urls = [
        item.get("url") for item in servers
        if isinstance(item, dict) and isinstance(item.get("url"), str)
    ] if isinstance(servers, list) else []
    if not server_urls and isinstance(document.get("host"), str):
        schemes = document.get("schemes")
        schemes = schemes if isinstance(schemes, list) and schemes else ["https"]
        base_path = document.get("basePath", "")
        server_urls = [f"{scheme}://{document['host']}{base_path}" for scheme in schemes]

    return {
        "provider": "EGID public OpenAPI contract",
        "openapi_version": document.get("openapi", document.get("swagger")),
        "server_urls": server_urls,
        "security_scheme_names": sorted(str(name) for name in security_schemes),
        "security_schemes": {
            str(name): {
                key: scheme[key]
                for key in ("type", "scheme", "name", "in", "bearerFormat", "flows")
                if key in scheme
            }
            for name, scheme in sorted(security_schemes.items())
            if isinstance(scheme, dict)
        },
        "relevant_operations": selected,
        "relevant_schemas": schema_summaries,
        "market_data_requested": False,
        "source_terms_verified": False,
        "historical_access_verified": False,
        "dataset_accepted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path for the contract metadata report")
    args = parser.parse_args(argv)
    try:
        report = summarize_openapi(fetch_openapi())
    except RuntimeError as exc:
        print(json.dumps({"status": "UNVERIFIED", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2

    report["status"] = "CONTRACT_DISCOVERED"
    report["retrieved_at_utc"] = datetime.now(UTC).isoformat()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
