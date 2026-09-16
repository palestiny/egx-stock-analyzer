# DEC-052 — Analysis Result Store MVP

## Status
Accepted — MVP

## Context

M12 needs to expose completed analysis through an API without re-running analysis from HTTP requests.

`DailyMarketAnalysis` already produces `DailyMarketAnalysisResult`, but there is currently no application boundary for retaining/querying completed stock analysis results.

## Decision

Introduce an application-level `AnalysisResultStore` boundary.

The MVP implementation is in-memory: `InMemoryAnalysisResultStore`.

## Responsibilities

The store owns only application-level result retention and lookup:

- `save(symbol, result)`
- `get(symbol)`

It does not:

- perform analysis
- calculate scores
- classify opportunities
- persist to a database
- expose HTTP
- own domain rules

## API Boundary

Future API queries will depend on the store/application query boundary rather than invoking the analysis pipeline directly.

```text
HTTP
 ↓
Application Query
 ↓
AnalysisResultStore
 ↓
Completed StockAnalysisResult
```

## MVP Limitations

In-memory storage is intentionally temporary.

The following are deferred:

- database persistence
- historical result retention
- execution/date-based indexing
- restart recovery
- multi-process/shared storage
- pagination

These require a separate persistence design gate.

## TDD

RED: `tests/test_analysis_result_store.py` defines save/get behavior.

GREEN: `InMemoryAnalysisResultStore` implements the contract.
