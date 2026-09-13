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

The assessment will also carry **structured quality issues/evidence** rather than a free-form reason string.

### Structured Quality Issues

`DataQualityIssue` is an immutable Value Object representing one piece of structured evidence associated with an assessment.

The accepted initial shape is:

```text
DataQualityAssessment
├── status
└── issues: zero or more DataQualityIssue values
```

Each issue uses a **structured code** rather than free-form text.

The initial representation of `DataQualityIssue.code` is a **dedicated Enum (`DataQualityIssueCode`)**. This provides a bounded, typo-safe vocabulary without introducing unnecessary abstraction at the current domain size.

The initial issue-code vocabulary is intentionally small and limited to currently meaningful generic data-quality findings:

```text
MISSING_VALUE
INVALID_VALUE
INVALID_TIMESTAMP
DUPLICATE_OBSERVATION
OHLC_INCONSISTENCY
```

These codes describe the type of quality finding only. They do **not** determine or infer whether the assessment is `VALID`, `INVALID`, `SUSPECT`, or `UNKNOWN`.

The code dependency will be kept localized to the issue model. If future requirements demonstrate that a richer Value Object is justified, the Enum can be replaced with a Value Object with limited impact on the surrounding domain model. We explicitly do **not** introduce an abstraction layer now solely to anticipate that possible change.

An issue does **not** determine or infer the assessment status. The assessment remains the authoritative classification; issues provide the structured evidence explaining that classification.

`VALID` assessments will normally contain no issues. The domain does not currently require an explicit invariant enforcing that relationship.

Optional contextual details may be introduced later if actual data-quality rules demonstrate a need for them. They are intentionally not part of the initial issue model.

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
- quality scores
- confidence values
- automatic assessment of `PriceBar`
- persistence concerns

`DataQualityIssue` is evidence only. It does not know about `PriceBar`, providers, or validation algorithms.

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
- Allows quality decisions to be explained in a structured, machine-readable form.
- Allows multiple independent quality findings to be attached to one assessment.
- Keeps the initial code representation simple while preserving a low-impact migration path to a richer Value Object if needed.

### Trade-offs

- The issue vocabulary adds another domain concept.
- The initial vocabulary is intentionally limited and may grow as real rules are introduced.
- Contextual issue details are deferred until a concrete rule demonstrates their need.
- Future provider/data-quality logic will require additional design work.
- A future migration from Enum to Value Object would require a controlled domain change if richer requirements emerge.

## Next Design Question

The initial issue-code vocabulary is now accepted as:

```text
MISSING_VALUE
INVALID_VALUE
INVALID_TIMESTAMP
DUPLICATE_OBSERVATION
OHLC_INCONSISTENCY
```

The representation decision remains:

> **Use an Enum for `DataQualityIssueCode` initially, keeping the dependency localized so a future migration to a Value Object remains low-impact if justified by real requirements.**

Implementation can now proceed with RED tests for `DataQualityIssue` and `DataQualityIssueCode`.

## Revisit Conditions

Revisit this decision when the project begins implementing actual data-quality rules for market observations, especially during M4 — Data Quality.
