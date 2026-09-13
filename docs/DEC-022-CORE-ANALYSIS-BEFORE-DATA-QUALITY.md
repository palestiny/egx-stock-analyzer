# DEC-022 — Core Analysis Before Data Quality

**Status:** Accepted
**Date:** 2026-09-13

## Context

The project needs both a reliable analytical core and a data-quality boundary.

Data Quality is important, but implementing its assessment rules before the analytical core is understood would risk designing validation around assumptions that the analysis does not yet require.

The current Data Quality Value Objects (`DataQualityAssessment`, `DataQualityIssue`, and `DataQualityIssueCode`) are already defined and tested. However, the responsibility and rule set for producing assessments are intentionally not complete.

The project should now prioritize understanding and implementing the core analytical logic from market observations through final analytical outputs, initially under the explicit assumption that the supplied observations are usable.

## Decision

The project will temporarily **defer implementation of the Data Quality assessment logic** and continue with the core analytical path first.

The current execution priority is:

```text
Market Observation
      ↓
Technical Analysis
      ↓
Fundamental Analysis
      ↓
Scoring
      ↓
Signal / Opportunity Detection
      ↓
Backtesting
      ↓
Reporting / Alerts
```

During this phase, test fixtures and controlled inputs may be treated as valid observations so that the analytical domain can be designed and exercised without waiting for provider-quality infrastructure.

The existing Data Quality model remains part of the domain boundary, but its assessment rules and `DataQualityAssessor` are deferred until the core analytical flow has been established.

## Important Boundary

This is **not** a decision that Data Quality is unimportant.

It is a sequencing decision:

```text
Core analytical capability first
            ↓
Understand real analytical requirements
            ↓
Return to Data Quality
            ↓
Build validation around actual requirements
```

The deferred Data Quality work must eventually sit before analysis in the operational pipeline:

```text
Raw Observation
      ↓
Data Quality Assessment
      ↓
Eligible Observation
      ↓
Analysis
```

The project therefore distinguishes between:

- **Designing the boundary now** — already done.
- **Implementing all validation rules now** — intentionally deferred.

## Trade-offs

### Advantages

- Reaches the project's core business value sooner.
- Prevents premature validation complexity.
- Lets actual analytical requirements drive future quality rules.
- Creates a complete vertical understanding of the analytical domain before infrastructure concerns dominate.
- Makes it easier to identify which data-quality checks genuinely affect analysis.

### Trade-offs

- The analysis core initially operates under a valid-data assumption.
- Some real-world data problems will not yet be handled.
- Provider integration and production reliability remain incomplete until the deferred work is resumed.

## Consequences

The next implementation work must begin with the analytical domain rather than additional Data Quality infrastructure.

No `DataQualityAssessor` implementation is required at this stage.

When Data Quality is resumed, the next design gate will determine:

1. What raw input the assessor receives.
2. Which quality rules exist.
3. How multiple issues map to assessment status.
4. How `VALID`, `SUSPECT`, `INVALID`, and `UNKNOWN` affect each analysis capability.

## Revisit Conditions

Return to Data Quality when the analytical core has reached a stable end-to-end vertical slice or when real provider data exposes quality requirements that materially affect analysis.
