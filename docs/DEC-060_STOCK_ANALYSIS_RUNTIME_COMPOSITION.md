# DEC-060 — Stock Analysis Runtime Composition

## Decision

Introduce `StockAnalysisRuntime` as the application-level composition boundary for the stock-analysis execution path.

The runtime composes:

`StockCatalog + AnalysisInputAssembler + AnalysisResultStore + RetryPolicy`

into:

`RunStockAnalysisBySymbol → RunStockAnalysis → DailyMarketAnalysis`

## Responsibilities

`create_stock_analysis_runtime` only wires already-defined application components.

It does not:

- create HTTP routes
- read environment variables
- create external API clients
- fetch market data
- fetch fundamentals
- perform analysis
- persist data

Infrastructure-specific provider construction remains outside this boundary.

## Why

The symbol-based use case now gives external callers a clean application entry point, while the existing analysis flow already depends on explicit abstractions. A small runtime object gives us one place to compose those application services without moving infrastructure concerns into the domain or use cases.

This also keeps the next infrastructure wiring step explicit: Yahoo Finance and Finnhub clients can be assembled later without changing `RunStockAnalysisBySymbol` or `RunStockAnalysis`.

## Deferred

- infrastructure-specific runtime factory
- environment/configuration loading
- HTTP execution endpoint
- scheduler trigger
- persistent result store
- production stock catalog
