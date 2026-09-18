# DEC-061 — Infrastructure Runtime Composition

## Decision

The infrastructure runtime is the composition boundary for stock-analysis execution.

For the current development vertical slice it creates and wires:

- `YahooFinanceHistoryClient`
- `YahooFinanceAdapter`
- `YahooFinanceFundamentalDataSource`
- `AnalysisInputAssembler`
- the existing application `StockAnalysisRuntime`

Yahoo Finance is currently used as the live data source for both market and fundamental data so that the system can be exercised on real EGX data without introducing a dependency on a separate financial-data provider.

This is a development/testing source decision, not a long-term provider commitment.

## Resource ownership

Yahoo Finance access through `yfinance` does not currently require a long-lived explicit HTTP client owned by the runtime. `close()` therefore exists as a lifecycle boundary but has no external client to release today.

## Boundaries

The infrastructure runtime may construct infrastructure data-source adapters and application dependencies, but it must not:

- perform stock analysis;
- calculate scores;
- contain domain rules;
- expose HTTP endpoints;
- fetch data during construction;
- resolve symbols by querying external services;
- persist analysis results.

## Current status

The previous Finnhub integration was blocked by a real HTTP 403 response: `You don't have access to this resource.` A direct request outside the application reproduced the same response, so the blocker was external to the application code.

For the current vertical-slice goal, the Finnhub dependency is removed from the runtime composition and Yahoo Finance is used for both market and annual fundamental data.

## Deferred

- production EGX stock master/catalog and authoritative synchronization;
- persistent result store;
- scheduled trigger wiring;
- multi-stock orchestration;
- final long-term data-source/provider architecture;
- reconciliation between multiple data sources;
- real EGX vertical-slice verification using the Yahoo Finance fundamental dataset.
