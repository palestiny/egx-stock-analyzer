# DEC-061 — Infrastructure Runtime Composition

## Decision

Introduce \`app/infrastructure/runtime.py\` as the infrastructure composition boundary for stock-analysis execution.

It is responsible for creating and wiring:

- \`YahooFinanceHistoryClient\`
- \`YahooFinanceAdapter\`
- \`HttpxFinnhubFinancialsClient\`
- \`FinnhubFundamentalDataProvider\`
- \`AnalysisInputAssembler\`
- the existing application \`StockAnalysisRuntime\`

The factory receives the \`StockCatalog\` explicitly and receives the \`yfinance\` module explicitly. Infrastructure configuration is represented by \`InfrastructureConfig\` and is passed explicitly to the factory.

## Resource ownership

The infrastructure runtime owns the Finnhub HTTP client. The returned runtime therefore exposes \`close()\` so the composition root can release the HTTP client without leaking infrastructure lifecycle concerns into the application layer.

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

The application runtime defined by DEC-060 remains infrastructure-agnostic. Infrastructure composition is kept outside \`app/application\` so external clients and resource lifecycle do not leak inward.

## Implementation Status

Implemented.

FastAPI lifecycle integration is implemented in \`app/main.py\`: the application created by \`create_application()\` uses a lifespan context that calls \`InfrastructureRuntime.close()\` during application shutdown. This keeps infrastructure resource ownership in the infrastructure runtime while allowing the composition root to manage its lifecycle.

Environment lookup is isolated in \`app/infrastructure/config.py\`. \`InfrastructureConfig.from_environment()\` reads \`FINNHUB_API_KEY\`, while \`HttpxFinnhubFinancialsClient\` requires the API key explicitly. The application composition root now exposes \`create_application_from_environment()\`, which loads \`InfrastructureConfig\` and passes it explicitly into \`create_infrastructure_runtime()\`. Environment access therefore remains outside the application and domain layers, and infrastructure dependencies are still not constructed at module import time.

The API now supports an explicit analysis trigger through \`POST /api/v1/analysis/{symbol}\`. The composition root passes \`RunStockAnalysisBySymbol\` into the API while preserving the existing result-query endpoint.

A development stock catalog is now available at \`app/infrastructure/stocks/development_catalog.py\`. It is intentionally limited to a small development seed and exists only to exercise composition and the first real-data vertical slice. It is not treated as the production EGX stock master.

The lifecycle, configuration, composition, API trigger, and development catalog behavior are covered by tests.

## Deferred

- production EGX stock master/catalog and authoritative synchronization;
- persistent result store;
- scheduled trigger wiring;
- multi-stock orchestration;
- real EGX vertical-slice verification with live provider credentials.
