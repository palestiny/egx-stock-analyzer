# DEC-062 — Configuration / Environment Composition

## Status

Accepted

## Context

The infrastructure runtime currently receives the Finnhub API key explicitly, while `InfrastructureConfig.from_environment()` already provides an infrastructure-level environment-loading boundary.

The remaining design question is how configuration should enter the runtime composition without allowing environment access to leak into the domain or application layers.

## Design Question

Where should environment variables be read, how should required configuration be validated, and how should that configuration reach infrastructure dependencies and the FastAPI composition root?

## Decision

Configuration is an infrastructure composition concern.

`InfrastructureConfig` is the configuration object for infrastructure dependencies. It is responsible for representing validated infrastructure configuration, while `InfrastructureConfig.from_environment()` is responsible for reading the process environment and validating required values.

The composition flow is:

```text
Environment
    ↓
InfrastructureConfig.from_environment()
    ↓
InfrastructureConfig
    ↓
InfrastructureRuntime composition
    ↓
Infrastructure adapters / clients
```

The application layer receives constructed dependencies and does not read environment variables.

The domain layer does not know that configuration exists.

`create_infrastructure_runtime()` will receive `InfrastructureConfig` explicitly rather than reading environment variables itself.

The FastAPI composition root may load `InfrastructureConfig` and construct the infrastructure runtime, then pass the runtime to `create_application()`. FastAPI lifecycle management remains responsible only for the runtime lifecycle; configuration loading is not a domain or application responsibility.

Configuration loading and runtime construction must not perform data fetching or external symbol resolution.

## Required Configuration

For the current infrastructure composition, the only required environment variable is:

```text
FINNHUB_API_KEY
```

Additional configuration values should be added to `InfrastructureConfig` only when an actual infrastructure requirement exists. We will not introduce a generic settings framework prematurely.

## Alternatives Considered

### Application layer reads environment variables

Rejected because it couples application use cases to process/environment concerns and weakens testability.

### Infrastructure client reads environment variables directly

Rejected because it hides a composition dependency inside the client and makes the client harder to construct deterministically in tests.

### Generic configuration/settings framework

Rejected for now because the project has only one required infrastructure setting and no demonstrated need for another abstraction.

### Pass individual configuration values forever

Rejected as the composition surface grows. An explicit infrastructure configuration object gives the composition boundary one stable dependency while keeping the values out of domain/application code.

## Trade-offs

We gain:

- explicit infrastructure dependencies;
- deterministic construction in tests;
- centralized required-configuration validation;
- no environment access in application/domain code;
- a small extension point for future infrastructure settings.

We accept:

- an additional infrastructure configuration type;
- the need for the composition root to explicitly load configuration;
- configuration remains infrastructure-specific rather than being a universal application settings object.

## Consequences

- `HttpxFinnhubFinancialsClient` continues to receive the API key explicitly.
- `InfrastructureRuntime` remains the infrastructure composition boundary.
- `StockAnalysisRuntime` remains configuration-agnostic.
- FastAPI remains a delivery/composition concern.
- No provider calls or symbol resolution occur while configuration is loaded or dependencies are constructed.

## Revisit Conditions

Revisit this decision if configuration becomes shared by domain/application behavior, if multiple deployment profiles require materially different configuration models, or if a broader configuration mechanism is justified by actual system complexity.
