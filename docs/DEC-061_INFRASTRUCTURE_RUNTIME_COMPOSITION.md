# DEC-061 — Infrastructure Runtime Composition

## Decision

Introduce `app/infrastructure/runtime.py` as the infrastructure composition boundary for stock-analysis execution.

It is responsible for creating and wiring:

- `YahooFinanceHistoryClient`
- `YahooFinanceAdapter`
- `HttpxFinnhubFinancialsClient`
- `FinnhubFundamentalDataProvider`
- `AnalysisInputAssembler`
- the existing application `StockAnalysisRuntime`

The factory receives the `StockCatalog` explicitly and receives the `yfinance` module explicitly. The Finnhub API key is passed explicitly to the factory; environment-variable lookup remains inside the existing Finnhub HTTP client.

## Resource ownership

The infrastructure runtime owns the Finnhub HTTP client. The returned runtime therefore exposes `close()` so the composition root can release the HTTP client without leaking infrastructure lifecycle concerns into the application layer.

## Boundaries

The infrastructure runtime may construct infrastructure adapters and application dependencies, but it must not:

- perform stock analysis;
- calculate scores;
- contain domain rules;
- expose HTTP endpoints;
- fetch data during construction;
- resolve symbols by querying external services;
- persist analysis results.

## Why

The application runtime defined by DEC-060 remains infrastructure-agnostic. Infrastructure composition is kept outside `app/application` so external clients and resource lifecycle do not leak inward.

## Deferred

- FastAPI lifespan integration;
- environment/configuration object;
- production stock master/catalog;
- persistent result store;
- scheduled trigger wiring;
- multi-stock orchestration;
- real EGX vertical-slice verification.
