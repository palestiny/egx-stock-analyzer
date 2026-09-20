# DEC-043 — Raw Observation to PriceBar Eligibility Boundary

## Status

Accepted.

## Context

`RawPriceBarObservation` represents external/raw market data. `PriceBar` represents the domain market-data value object consumed by core analysis.

Data Quality is responsible for deciding whether a raw observation is eligible for analytical use.

## Decision

Create `PriceBar` only from a raw observation whose `DataQualityAssessment` is `VALID`.

The conversion boundary:

```text
RawPriceBarObservation
        ↓
DataQualityAssessment
        ↓
VALID ?
   ↓ yes
PriceBar
```

`SUSPECT`, `INVALID`, and `UNKNOWN` observations are not converted into `PriceBar` by this boundary.

## Responsibilities

The converter:

- maps raw OHLCV values into the existing `Price`, `Volume`, and `PriceBar` domain objects;
- requires a `VALID` assessment;
- does not perform additional provider-specific validation;
- does not modify raw values;
- does not re-run Data Quality rules;
- does not own persistence or provider integration.

The converter is a boundary, not a second validation system.

## Trade-off

Requiring `VALID` avoids allowing questionable observations into the analytical core, while keeping the raw observation available for diagnostics and future quality-policy changes.

## Deferred

- batch conversion policy;
- persistence of rejected observations;
- provider-specific normalization;
- trading-calendar validation;
- data repair/imputation;
- quality thresholds beyond the current MVP rules.

## TDD Acceptance

1. A valid observation converts to a `PriceBar`.
2. Suspect observations are rejected.
3. Invalid observations are rejected.
4. Unknown observations are rejected.
5. Raw values are preserved in the resulting domain objects.
6. Conversion is deterministic.
7. The converter does not mutate the raw observation or assessment.
