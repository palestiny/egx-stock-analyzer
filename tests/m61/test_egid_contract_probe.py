from __future__ import annotations

from tools.m61_egid_contract_probe import summarize_openapi


def test_summary_extracts_history_contract_without_market_data_or_examples():
    document = {
        "openapi": "3.0.1",
        "servers": [{"url": "https://ticker.egidegypt.com"}],
        "security": [{"BearerAuth": []}],
        "paths": {
            "/api/DelayedFeed/getSymbolHistory": {
                "post": {
                    "operationId": "DelayedFeed_getSymbolHistory",
                    "summary": "Get symbol history",
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {
                            "name": "symbol",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HistoryReqDto"},
                                "example": {"symbol": "COMI"},
                            }
                        },
                    },
                    "responses": {"200": {"description": "Success"}},
                }
            },
            "/api/Feed/GetTodayMarketWatch": {
                "get": {"operationId": "GetTodayMarketWatch", "responses": {"200": {}}}
            },
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
            "schemas": {
                "HistoryReqDto": {
                    "type": "object",
                    "required": ["symbol", "fromDate", "toDate"],
                    "properties": {
                        "symbol": {"type": "string"},
                        "fromDate": {"type": "string", "format": "date"},
                        "toDate": {"type": "string", "format": "date"},
                    },
                }
            },
        },
    }

    report = summarize_openapi(document)

    assert report["market_data_requested"] is False
    assert report["dataset_accepted"] is False
    assert report["security_scheme_names"] == ["BearerAuth"]
    assert len(report["relevant_operations"]) == 1
    operation = report["relevant_operations"][0]
    assert operation["path"] == "/api/DelayedFeed/getSymbolHistory"
    assert operation["method"] == "POST"
    assert operation["request_body"]["required"] is True
    assert operation["response_codes"] == ["200"]
    schema = report["relevant_schemas"]["HistoryReqDto"]
    assert schema["required"] == ["symbol", "fromDate", "toDate"]
    assert schema["properties"]["fromDate"]["format"] == "date"
    assert "example" not in str(report)


def test_summary_handles_swagger_v2_and_missing_optional_contract_sections():
    report = summarize_openapi(
        {
            "swagger": "2.0",
            "paths": {
                "/api/Feed/GetSymbolHistories": {
                    "get": {
                        "operationId": "GetSymbolHistories",
                        "parameters": [],
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }
    )

    assert report["openapi_version"] == "2.0"
    assert report["security_scheme_names"] == []
    assert report["relevant_operations"][0]["method"] == "GET"
    assert report["relevant_operations"][0]["request_body"] is None


def test_summary_rejects_missing_paths():
    try:
        summarize_openapi({"openapi": "3.0.1"})
    except ValueError as exc:
        assert "missing paths" in str(exc)
    else:
        raise AssertionError("missing OpenAPI paths should be rejected")
