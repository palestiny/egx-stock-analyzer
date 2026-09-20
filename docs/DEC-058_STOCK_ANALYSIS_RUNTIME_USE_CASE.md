# DEC-058 — Stock Analysis Runtime Use Case

## Decision

Add `RunStockAnalysis` as the application use case that composes the existing boundaries for a single stock:

`Stock + as_of → AnalysisInputAssembler → StockAnalysisInput → DailyMarketAnalysis → AnalysisResultStore`

## Responsibilities

`RunStockAnalysis` owns orchestration only. It does not:

- fetch provider data directly
- construct financial metrics
- perform technical/fundamental scoring
- implement opportunity rules
- expose HTTP endpoints
- persist results itself

Those responsibilities remain behind their existing boundaries.

## Why

`AnalysisInputAssembler` already owns the conversion from acquired data into the complete `StockAnalysisInput`. `DailyMarketAnalysis` already owns execution lifecycle, retry behavior, analysis invocation, and result-store integration. The missing application-level piece was a small use case that composes them without duplicating either responsibility.

## Explicit constraint

The use case currently requires `DailyMarketAnalysis` to finish with `ExecutionState.COMPLETED`. `COMPLETED_WITH_ERRORS`, `FAILED`, and `CANCELLED` are surfaced as a runtime failure to the caller rather than being silently treated as success.

## Deferred

- multi-stock orchestration
- stock catalog/universe management
- HTTP trigger endpoint
- scheduler wiring
- persistent result storage
- production fundamental-data credential/configuration
