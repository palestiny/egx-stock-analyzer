# DEC-044 — Data Acquisition Boundary MVP

## Status

Accepted.

## Context

The analytical core must remain independent from external market-data providers. External sources may expose different symbols, formats, timestamps, availability, authentication, limits, and failure behavior.

Current domain flow already establishes:

```text
Raw Observation
      ↓
Data Quality Assessment
      ↓
VALID
      ↓
PriceBar
      ↓
Core Analysis
```

M3 introduces the external acquisition boundary without moving provider concerns into the domain.

## Decision

Use a provider-neutral acquisition port in the application/infrastructure boundary.

The provider adapter returns `RawPriceBarObservation` objects. It does not create `PriceBar` and does not perform analytical decisions.

```text
Application / Use Case
        ↓
MarketDataProvider interface
        ↓
Provider Adapter
        ↓
External API / Dataset
        ↓
RawPriceBarObservation
        ↓
Data Quality
        ↓
PriceBar
```

The core domain does not depend on a specific provider.

## MVP Contract

The acquisition capability must support requesting daily market observations for a stock and a bounded time range.

Conceptually:

```text
get_daily_observations(stock, from, to)
        → RawPriceBarObservation[*]
```

The exact Python protocol/interface shape is part of the implementation RED step and must remain small.

## Provider Adapter Responsibilities

A provider adapter owns:

- authentication and credentials;
- provider-specific symbol mapping;
- HTTP/client mechanics;
- pagination and provider-specific rate limits;
- provider response parsing;
- provider-specific timestamps and field names;
- conversion of provider records into `RawPriceBarObservation`.

It must not own:

- `PriceBar` domain validation;
- technical analysis;
- fundamental analysis;
- scoring;
- opportunity classification;
- trading decisions.

## Error Boundary

Provider failures must remain distinguishable from data-quality problems.

Examples:

```text
Provider unavailable      → acquisition failure
Authentication failure    → acquisition failure
Rate limited              → acquisition failure
Malformed provider record → raw observation / quality concern
Negative OHLC value       → data quality concern
OHLC inconsistency        → data quality concern
```

The MVP does not silently substitute another provider. Fallback requires a separate design decision because it affects reproducibility and source attribution.

## Source Attribution

The raw observation itself remains provider-neutral. Provider/source metadata belongs to the acquisition boundary or an explicitly designed metadata object; it must not be added to `PriceBar` merely because a provider exists.

## Initial Provider Strategy

Do not hard-code a production provider in the domain.

For the first implementation, use a replaceable adapter and a deterministic fixture/fake for tests. Select the real external provider only after verifying its current API contract, EGX coverage, historical daily availability, authentication, and licensing/usage terms.

Current web research found multiple EGX data options, including paid historical/intraday datasets and newer API offerings, but this is not sufficient by itself to commit the project to one vendor.

## Reproducibility

Acquisition must make the source and requested period observable at the application boundary. Historical analysis must be reproducible from the acquired raw observations rather than from a live provider response that may change later.

## Excluded from M3 MVP

- automatic provider fallback;
- live trading/order execution;
- WebSocket streaming;
- intraday acquisition;
- database persistence;
- caching strategy;
- retry policy beyond what is required to isolate provider failure;
- corporate-action adjustment;
- missing-day inference;
- data repair;
- technical/fundamental analysis;
- scoring and opportunity classification.

## TDD Acceptance

1. The application can request bounded daily observations through a provider-neutral port.
2. A provider adapter returns `RawPriceBarObservation` objects.
3. Provider-specific response parsing stays outside the domain.
4. The core domain imports no concrete provider implementation.
5. Provider failure is distinguishable from a returned data-quality assessment.
6. Tests use a deterministic fake/fixture provider rather than a live network.
7. The adapter does not create `PriceBar` directly.
8. The same provider response maps deterministically to the same raw observations.

## Trade-offs

### Provider-neutral port vs direct provider integration

Provider-neutral port adds a small abstraction but protects the domain from vendor lock-in and makes deterministic tests possible.

### No automatic fallback vs fallback

No fallback keeps source behavior and reproducibility explicit. Fallback can be added later after defining source precedence and provenance.

### Raw observation vs immediate PriceBar

Raw observation preserves provider data and allows Data Quality to assess it before analytical use.

## Next Gate

After the provider-neutral port and deterministic adapter test slice are green, perform a separate provider selection decision before connecting a live EGX source.
