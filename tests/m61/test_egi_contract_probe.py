from __future__ import annotations

import hashlib

from tools.m61_egi_contract_probe import inspect_swagger


def test_inspector_extracts_request_and_response_schema_without_market_data():
    raw = b'{"openapi":"3.0.0"}'
    payload = {
        "components": {
            "schemas": {
                "HistoryReqDto": {
                    "type": "object",
                    "required": ["symbol", "fromDate"],
                    "properties": {
                        "symbol": {"type": "string"},
                        "fromDate": {"type": "string", "format": "date"},
                    },
                },
                "HistoryRow": {
                    "type": "object",
                    "properties": {"close": {"type": "number"}},
                },
            }
        },
        "paths": {
            "/api/Feed/GetSymbolHistory": {
                "post": {
                    "operationId": "GetSymbolHistory",
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/HistoryReqDto"}}
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/HistoryRow"}}
                            },
                        }
                    },
                }
            }
        },
    }
    report = inspect_swagger(payload, 200, raw)
    operation = next(item for item in report["operations"] if item["path"] == "/api/Feed/GetSymbolHistory")
    assert report["status"] == "CONTRACT_FOUND"
    assert report["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert operation["request_body"]["application/json"]["$ref"] == "HistoryReqDto"
    assert operation["request_body"]["application/json"]["definition"]["required"] == ["symbol", "fromDate"]
    assert operation["responses"]["200"]["content"]["application/json"]["$ref"] == "HistoryRow"
    assert "No market-history operation was invoked." in report["limitations"]


def test_inspector_fails_closed_when_swagger_is_unavailable():
    report = inspect_swagger({"error": "not found"}, 404, b"not found")
    assert report["status"] == "UNAVAILABLE"
    assert report["found_target_operations"] if "found_target_operations" in report else True


def test_inspector_handles_unexpected_swagger_shape():
    report = inspect_swagger({"paths": []}, 200, b'{"paths":[]}')
    assert report["status"] == "INVALID_SWAGGER"
    assert report["error"] == "paths_not_object"
