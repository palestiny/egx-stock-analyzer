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

For a missing result, the MVP returns HTTP 200 with:

```json
{
  "symbol": "EGAL",
  "status": "not_found"
}
```

## Why HTTP 200 for missing results in MVP
The first API slice is intentionally focused on exposing the read capability without introducing an HTTP error policy as a separate domain/application concern. A future API contract can change missing-resource semantics to HTTP 404 through an explicit decision.

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
- HTTP 404 policy
- filtering/sorting
- detailed analysis evidence DTOs
- dashboard-specific aggregation endpoints
