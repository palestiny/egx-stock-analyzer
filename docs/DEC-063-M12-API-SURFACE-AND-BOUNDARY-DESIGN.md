# DEC-063 — M12 API Surface and Boundary Design

**Status:** Accepted for the first M12 API slice  
**Date:** 2026-09-18

## Context

M12 has reached a validated runtime/API foundation. The application can execute an analysis by stock symbol and expose the stored analysis result through FastAPI.

The next risk is allowing the API layer to grow by adding endpoints and business rules directly in FastAPI without first defining the application-facing contract.

## Decision

The first M12 API surface is intentionally split into two capabilities:

### Query

`GET /api/v1/analysis/{symbol}`

Reads the latest stored analysis result through the application `GetAnalysisResult` use case.

### Command

`POST /api/v1/analysis/{symbol}`

Requests analysis through `RunStockAnalysisBySymbol`, then returns the resulting stored analysis.

FastAPI remains an adapter. Business rules stay in application/domain layers.

## Boundary Rules

The API layer may own:

- HTTP routing.
- HTTP status mapping.
- Request parsing.
- Response DTO construction.
- Transport-level validation.

The API layer must not own:

- scoring formulas;
- opportunity classification rules;
- technical/fundamental analysis;
- stock lookup rules;
- retry policy;
- data-quality rules;
- provider selection;
- persistence behavior.

## Error Semantics

For the current slice:

- unknown stock symbol → HTTP 404;
- requested result not found → HTTP 404;
- analysis execution not configured → HTTP 503;
- analysis execution failure → HTTP 500;
- successful analysis → HTTP 200.

These mappings are transport semantics, not domain business rules.

The exact public error schema remains open for a later API-contract refinement.

## Response Boundary

`AnalysisResultResponse` is the transport DTO.

The API must not expose domain objects directly.

The current response contains:

- symbol;
- technical score;
- fundamental score;
- stock quality;
- entry quality;
- opportunity classification.

Additional fields require an explicit API contract decision rather than being added opportunistically.

## Freshness

The current `GET` endpoint means:

> return the latest analysis result currently available in the configured result store.

It does not imply that the result is current as of today, nor does it perform analysis.

Freshness metadata and historical-result retrieval are deferred.

## Dashboard Boundary

A future dashboard consumes API/application capabilities and owns presentation concerns only.

Dashboard behavior must not become a second implementation of analysis or scoring rules.

## Deferred

The following remain outside this first API slice:

- authentication/authorization;
- persistent result history;
- freshness/version metadata;
- historical analysis endpoints;
- report endpoints;
- alert endpoints;
- pagination/filtering;
- dashboard implementation;
- structured production error taxonomy;
- production observability.

These are candidates for later M12 design gates or M13 where appropriate.

## Alternatives Considered

### Put business logic in FastAPI

Rejected because it would couple domain behavior to the transport layer and make the API a second business layer.

### Expose domain objects directly

Rejected because it leaks domain representation into the public transport contract.

### Build the complete dashboard before stabilizing the API

Rejected because it would allow UI requirements to shape application/domain boundaries prematurely.

## Consequences

The current API remains deliberately small.

Future endpoints must be justified by an application capability and documented before implementation.

The API can evolve independently from the domain model as long as the DTO and transport boundaries remain explicit.
