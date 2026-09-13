# DEC-021 — Data Quality Assessment Status and Analysis Eligibility

**Status:** Accepted
**Date:** 2026-09-13

## Context

The project treats external market data as an observation rather than absolute truth. Data quality is therefore a separate concern from the `PriceBar` representation.

The next domain step was to define the minimal vocabulary and behavior of a data-quality assessment without introducing provider-specific validation rules or embedding data-quality logic inside `PriceBar`.

## Decision

The domain uses a separate immutable `DataQualityAssessment` value object with a `DataQualityStatus` vocabulary containing:

```text
VALID
INVALID
SUSPECT
UNKNOWN
```

The assessment exposes:

```text
is_eligible_for_analysis()
```

The eligibility rule is:

```text
VALID    -> eligible
INVALID  -> not eligible
SUSPECT  -> not eligible
UNKNOWN  -> not eligible
```

Therefore, **only `VALID` data is currently eligible for analysis**.

## TDD Progress

The behavior was developed incrementally using RED -> GREEN.

Completed tests cover:

1. `DataQualityAssessment` can represent `VALID`.
2. `DataQualityAssessment` can represent `INVALID`.
3. `DataQualityAssessment` can represent `SUSPECT`.
4. `DataQualityAssessment` can represent `UNKNOWN`.
5. `VALID` is eligible for analysis.
6. `INVALID`, `SUSPECT`, and `UNKNOWN` are not eligible for analysis.

The non-`VALID` behavior is covered through parameterized testing rather than duplicating three equivalent test functions.

## Current Domain Boundary

`DataQualityAssessment` does **not** currently decide why an observation received its status.

It does not yet contain:

- provider-specific validation rules
- OHLC validation rules
- reason/error collections
- quality scores
- confidence values
- automatic assessment of `PriceBar`
- persistence concerns

Those are separate design questions and must not be introduced without a design decision.

## Relationship to PriceBar

The current flow is:

```text
External Observation
        |
        v
     PriceBar
        |
        v
Data Quality Assessment
        |
        v
Analysis Eligibility
```

`PriceBar` remains responsible for representing the observation itself. `DataQualityAssessment` is responsible for classifying its quality and determining whether the current analysis pipeline may use it.

## Trade-offs

### Advantages

- Keeps external observations separate from quality judgments.
- Prevents `PriceBar` from becoming a validation object.
- Makes analysis eligibility explicit and testable.
- Provides a small stable vocabulary for future data-quality rules.

### Trade-offs

- The current assessment cannot explain the reason behind a status.
- The actual rules that produce each status are still undefined.
- Future provider/data-quality logic will require additional design work.

## Next Design Question

Before adding more behavior, decide whether `DataQualityAssessment` needs to carry the **reason/evidence** behind a quality status.

Possible directions include:

1. Keep status-only for now.
2. Add a simple reason.
3. Add structured quality issues/evidence.

No option is implemented yet.

## Revisit Conditions

Revisit this decision when the project begins implementing actual data-quality rules for market observations, especially during M4 — Data Quality.
