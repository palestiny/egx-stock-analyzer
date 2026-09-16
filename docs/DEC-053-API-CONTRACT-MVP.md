# DEC-053 — Analysis API Contract MVP

## Status
Accepted

## Context
M12 exposes completed stock-analysis results through an HTTP API. The API must remain an adapter over the application layer and must not expose domain objects directly.

## Decision
The MVP exposes:

`GET /api/v1/analysis/{symbol}`

The endpoint uses `GetAnalysisResult` and `AnalysisResultStore` to read an existing result. It does not execute analysis.

For an available result, the API response contains:

```json
{
  "symbol": "EGAL",
  "technical_score": 0,
  "fundamental_score": 2,
  "stock_quality": 2,
  "entry_quality": 1,
  "opportunity": "buy"
}
```

For a missing result, the MVP returns HTTP 404 with:

```json
{
  "detail": "Analysis result not found for EGAL"
}
```

## HTTP missing-resource policy
The API boundary uses HTTP 404 when the requested analysis result does not exist. This is an HTTP adapter concern and does not introduce missing-resource semantics into the domain or application layer.

## Response boundary
`AnalysisResultResponse` is an API DTO. The API maps the application result into this DTO before serialization. Domain/application models are not returned directly from the HTTP boundary.

## Included fields
- symbol
- technical_score
- fundamental_score
- stock_quality
- entry_quality
- opportunity

Detailed technical/fundamental evidence is intentionally deferred until a concrete dashboard/use-case requires it.

## Deferred
- pagination
- historical analysis endpoints
- database-backed queries
- authentication/authorization
- filtering/sorting
- detailed analysis evidence DTOs
- dashboard-specific aggregation endpoints
