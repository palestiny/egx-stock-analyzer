# DEC-021 — Data Quality Assessment Status and Analysis Eligibility

**Status:** Accepted
**Date:** 2026-09-13

## Context

The project treats external market data as an observation rather than absolute truth. Data quality is therefore a separate concern from the `PriceBar` representation.

The domain first defines the minimal vocabulary and behavior of a data-quality assessment without introducing provider-specific validation rules or embedding data-quality logic inside `PriceBar`.

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

The current eligibility rule is:

```text
VALID    -> eligible
INVALID  -> not eligible
SUSPECT  -> not eligible
UNKNOWN  -> not eligible
```

Therefore, **only `VALID` data is currently eligible for analysis**.

The assessment also carries **structured quality issues/evidence** rather than a free-form reason string.

### Structured Quality Issues

`DataQualityIssue` is an immutable Value Object representing one piece of structured evidence associated with an assessment.

The accepted shape is:

```text
DataQualityAssessment
├── status
└── issues: zero or more DataQualityIssue values
```

Each issue uses a **structured code** rather than free-form text.

The initial representation of `DataQualityIssue.code` is a **dedicated Enum (`DataQualityIssueCode`)**. This provides a bounded, typo-safe vocabulary without introducing unnecessary abstraction at the current domain size.

The initial issue-code vocabulary is:

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

Optional contextual details may be introduced later if actual data-quality rules demonstrate a need for them.

## TDD Progress

The behavior was developed incrementally using RED -> GREEN.

Completed tests cover the status/eligibility behavior, structured issue codes, issue immutability, assessment issues, and assessment immutability.

The full project test suite was passing at the time this decision was documented.

## Current Domain Boundary

`DataQualityAssessment` does **not** currently decide why an observation received its status.

It does not currently contain:

- provider-specific validation rules
- OHLC validation rules
- quality scores
- confidence values
- automatic assessment of `PriceBar`
- persistence concerns

`DataQualityIssue` is evidence only. It does not know about `PriceBar`, providers, or validation algorithms.

### Assessment Responsibility Is Deferred

The project intentionally has **not** implemented a `DataQualityAssessor` yet.

The responsibility for creating an assessment from raw observations will be designed and implemented later, after the core analytical path has been established.

The future operational boundary is expected to be:

```text
Raw Observation
      ↓
Data Quality Assessment
      ↓
Eligible Observation
      ↓
Analysis
```

The exact input, rule composition, and status-mapping policy remain open until Data Quality work is resumed.

## Relationship to PriceBar

`PriceBar` remains responsible for representing a market observation itself. It does not own data-quality rules.

The currently committed domain boundary is:

```text
Raw Observation
      ↓
Data Quality Boundary
      ↓
PriceBar / Eligible Observation
      ↓
Analysis
```

During the current core-analysis phase, controlled test observations may be treated as valid so that analytical logic can be developed without waiting for provider-quality infrastructure.

## Sequencing Decision

The project has explicitly decided to prioritize the core analytical path before implementing the full data-quality assessment logic.

See:

```text
docs/DEC-022-CORE-ANALYSIS-BEFORE-DATA-QUALITY.md
```

The Data Quality model is therefore **defined but temporarily frozen**. This is a sequencing decision, not a removal of the Data Quality requirement.

## Trade-offs

### Advantages

- Keeps external observations separate from quality judgments.
- Prevents `PriceBar` from becoming a validation object.
- Makes analysis eligibility explicit and testable.
- Provides a small stable vocabulary for future data-quality rules.
- Allows multiple independent quality findings to be attached to one assessment.
- Avoids premature validation complexity while the analytical domain is still being discovered.

### Trade-offs

- The issue vocabulary adds another domain concept.
- The initial vocabulary may grow as real rules are introduced.
- Contextual issue details are deferred until concrete rules demonstrate their need.
- Provider/data-quality logic remains incomplete during the current analytical-core phase.
- A future migration from Enum to Value Object would require a controlled domain change if richer requirements emerge.

## Revisit Conditions

Return to Data Quality when the analytical core has reached a stable end-to-end vertical slice or when real provider data exposes quality requirements that materially affect analysis.

At that point, the next design gate must decide:

1. What raw input the assessor receives.
2. Which quality rules exist.
3. How multiple issues map to assessment status.
4. How quality status affects each analysis capability.
