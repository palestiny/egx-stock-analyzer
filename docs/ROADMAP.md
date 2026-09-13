# EGX Stock Analyzer — Roadmap

**Project:** EGX Stock Analyzer  
**Status:** Active  
**Master Plan:** This document is the project roadmap and the primary place to track planned execution order and current position.

---

# 1. Purpose

This roadmap defines the planned evolution of the EGX Stock Analyzer from its domain foundation into an automated, explainable stock-analysis platform.

A milestone is complete only when its design, tests, implementation, review/refactor, documentation, Git commit, and acceptance criteria are satisfied.

The roadmap may change when new evidence or requirements justify a deliberate design decision.

---

# 2. Development Strategy

The project is intentionally developed in two broad tracks:

```text
CORE ANALYTICAL TRACK
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

RELIABILITY / OPERATIONS TRACK
Raw Provider Data
  ↓
Data Acquisition
  ↓
Data Quality Assessment
  ↓
Automation
  ↓
Production Reliability
```

The current priority is the **Core Analytical Track**.

Data Quality is an important domain boundary and its basic Value Objects are already defined, but detailed assessment logic is intentionally deferred until the analytical core is understood end-to-end. See `docs/DEC-022-CORE-ANALYSIS-BEFORE-DATA-QUALITY.md`.

This does **not** mean Data Quality is optional. It means its implementation is sequenced after the core analytical path.

We intentionally avoid starting with:

- UI
- database-heavy architecture
- AI-first architecture
- microservices
- complex infrastructure
- authentication
- production deployment concerns

The core analytical model must become understandable, deterministic, explainable, and testable first.

---

# 3. Milestone Overview

| Milestone | Name | Status | Current Intent |
|---|---|---|---|
| M0 | Vision & Blueprint | 🟡 In Progress | Keep project direction and engineering method explicit |
| M1 | Domain Foundation | 🟡 In Progress | Establish stable core domain concepts |
| M2 | Market Data Foundation | 🟡 In Progress | Establish market observation semantics |
| M3 | Data Acquisition | 🔴 Deferred | External providers after core behavior is understood |
| M4 | Technical Analysis | 🟡 Next | Build the first core analytical capability |
| M5 | Fundamental Analysis | 🔴 Not Started | Build company-quality analysis |
| M6 | Scoring Engine | 🔴 Not Started | Combine analytical evidence into explainable scores |
| M7 | Signal Generation | 🔴 Not Started | Produce explainable opportunity classifications |
| M8 | Backtesting | 🔴 Not Started | Validate analytical strategies historically |
| M9 | Data Quality | 🟡 Foundation Defined / Implementation Deferred | Implement real quality rules after the core analytical flow |
| M10 | Automation | 🔴 Not Started | Execute the analytical pipeline automatically |
| M11 | Reporting & Alerts | 🔴 Not Started | Deliver analytical results |
| M12 | API & Dashboard | 🔴 Not Started | Expose application capabilities |
| M13 | Production Hardening | 🔴 Not Started | Reliability, security, observability, deployment |

The milestone numbering is retained to preserve project history. The **execution order has been deliberately adjusted** so the core analytical path is built before the detailed Data Quality implementation.

---

# 4. Current Position — IMPORTANT

## Where We Stopped

The project has completed the current Data Quality model foundation:

- `DataQualityStatus`
- `DataQualityAssessment`
- `DataQualityIssue`
- `DataQualityIssueCode`
- Initial issue vocabulary
- Analysis eligibility behavior
- Immutability tests

The implementation and tests were committed and pushed to GitHub.

The full test suite was passing at the end of this milestone.

## What Is Frozen For Now

Do **not** continue implementing:

- `DataQualityAssessor`
- detailed validation rules
- provider-specific quality rules
- status-mapping policies
- advanced data-quality infrastructure

Those are deliberately deferred.

## Next Step

**Begin the Core Analytical Track at M4 — Technical Analysis.**

The immediate design gate is therefore **not Data Quality**. It is the first technical-analysis domain capability: what the system means by technical evidence and what the first analysis capability should be.

---

# 5. M0 — Vision & Project Blueprint

## Objective

Define the purpose, boundaries, philosophy, architecture direction, and success criteria.

## State

Foundation exists and continues to evolve as important sequencing and architecture decisions are made.

---

# 6. M1 — Domain Foundation

## Objective

Build the smallest stable domain model required by the system.

## Established Concepts

Current committed domain concepts include:

```text
Stock
Price
Volume
Timeframe
PriceBar
DataQualityAssessment
DataQualityIssue
DataQualityIssueCode
```

The project uses Domain-First design and TDD. Concepts are added only when justified by a real domain responsibility.

## Rules

Domain logic remains independent from:

- database
- HTTP
- external providers
- UI
- AI
- infrastructure

---

# 7. M2 — Market Data Foundation

## Objective

Define how the system represents market observations.

## Established Direction

`PriceBar` represents an immutable market observation containing:

```text
Stock
Timeframe
Timestamp
Open
High
Low
Close
Volume
```

The logical observation identity is:

```text
Stock + Timeframe + Timestamp
```

`PriceBar` does not own provider rules, data-quality rules, trading-calendar rules, indicators, strategy, or alerts.

Daily timeframe is the MVP timeframe.

Detailed time/session semantics are documented separately in `docs/DEC-020-PRICEBAR-TIME-SEMANTICS.md`.

---

# 8. M3 — Data Acquisition

## Objective

Connect external market-data providers.

## Deferred Until

The analytical domain has enough shape to define exactly what data the analysis requires.

## Future Direction

```text
External Provider
       ↓
Provider Adapter
       ↓
Raw Observation
       ↓
Data Quality
       ↓
Analysis
```

Provider-specific behavior must remain outside the core domain.

---

# 9. M4 — Technical Analysis

## Objective

Transform market observations into deterministic, explainable technical evidence.

## First Design Gate

Before implementation, decide:

- What is a technical analysis result?
- What is its relationship to `PriceBar`?
- What is the smallest useful first capability?
- Which calculations belong in the domain?
- Which configuration belongs outside the result?
- How are historical windows represented?
- How are insufficient observations handled?
- What makes the result deterministic and reproducible?

## Candidate Capabilities

Potential future capabilities include:

- trend detection
- support detection
- resistance detection
- moving averages
- momentum indicators
- volatility
- breakouts
- gaps
- volume analysis

The final indicator set is not yet committed.

## Principle

Start with the smallest capability that advances the analytical core. Do not build a complete indicator library before the domain meaning is clear.

---

# 10. M5 — Fundamental Analysis

## Objective

Evaluate the financial quality of companies.

Potential evidence:

- revenue growth
- earnings growth
- profitability
- debt
- cash flow
- valuation
- ROE
- margins
- dividends

The exact metrics will be selected based on strategy requirements and reliable data availability.

Fundamental analysis must eventually account for reporting periods, missing data, restatements, accounting periods, corporate actions, and freshness.

---

# 11. M6 — Scoring Engine

## Objective

Combine analytical evidence into consistent, explainable scores.

The working proposal remains:

```text
Technical       30
Fundamental     25
Momentum        15
Liquidity       15
Catalysts       10
Risk             5
------------------
Total           100
```

These weights are **not final business rules**.

The scoring system must eventually be deterministic, explainable, testable, configurable, and versioned.

### Important Separation

The project explicitly distinguishes:

```text
Stock Quality
```

from:

```text
Entry Quality
```

This is a committed design decision.

---

# 12. M7 — Signal Generation

## Objective

Transform analytical evidence into actionable classifications.

Initial working labels:

```text
BUY
WATCH
HOLD
AVOID
```

Future signals may include:

```text
Signal
Score
Entry Zone
Stop Loss
Target 1
Target 2
Risk / Reward
Confidence
Reasons
Risks
Strategy Version
Generated At
```

The exact rules remain to be designed.

Signals must be explainable.

---

# 13. M8 — Backtesting

## Objective

Determine whether strategies would have worked historically.

Backtesting must eventually address:

- look-ahead bias
- data leakage
- survivorship bias where relevant
- future-information leakage
- realistic execution assumptions

Results must be reproducible from:

```text
Historical Data
+
Strategy Version
+
Configuration
```

---

# 14. M9 — Data Quality

## Objective

Assess whether observations are usable for analysis.

## Foundation Already Defined

```text
DataQualityAssessment
├── status
└── issues
```

Statuses:

```text
VALID
SUSPECT
INVALID
UNKNOWN
```

Initial issue codes:

```text
MISSING_VALUE
INVALID_VALUE
INVALID_TIMESTAMP
DUPLICATE_OBSERVATION
OHLC_INCONSISTENCY
```

## Current State

**Foundation defined; implementation of assessment rules intentionally deferred.**

When resumed, the next design gate must decide:

1. Raw input to the assessor.
2. Quality rules.
3. Multiple-issue status mapping.
4. Effect of quality status on each analysis capability.

See `docs/DEC-021-DATA-QUALITY-ASSESSMENT.md` and `docs/DEC-022-CORE-ANALYSIS-BEFORE-DATA-QUALITY.md`.

---

# 15. M10 — Automation

## Objective

Run the analytical pipeline automatically.

Target flow:

```text
Collect
  ↓
Assess Data Quality
  ↓
Analyze
  ↓
Score
  ↓
Rank
  ↓
Detect Opportunities
  ↓
Generate Report
```

Scheduling may eventually be daily, event-driven, or market-session based.

---

# 16. M11 — Reporting & Alerts

## Objective

Deliver useful results.

Potential outputs:

- daily market report
- top opportunities
- watchlist changes
- new signals
- risk alerts
- data-quality alerts
- strategy-performance reports

Potential channels include email, Telegram, web notifications, and dashboard notifications. Provider choices are not committed.

---

# 17. M12 — API & Dashboard

## Objective

Expose application capabilities to users.

Potential capabilities:

- stock search
- stock details
- historical data
- analysis
- scores
- signals
- reports
- strategy results
- backtests
- alerts

API/UI must consume application/domain capabilities and must not own business rules.

---

# 18. M13 — Production Hardening

## Objective

Prepare the system for reliable long-term operation.

Areas include:

- reliability
- retries
- failure recovery
- idempotency
- monitoring
- secrets management
- authentication/authorization
- performance
- caching
- observability
- deployment
- backups
- migrations
- rollback

These concerns are intentionally later-stage concerns.

---

# 19. Cross-Cutting Requirements

These apply across milestones.

## Correctness

Results must be mathematically and logically correct.

## Explainability

Important outputs must have understandable reasons.

## Reproducibility

Historical results should be reproducible.

## Testability

Important behavior must be independently testable.

## Replaceability

External providers and AI implementations must remain replaceable.

## Extensibility

New strategies and indicators should not require rewriting unrelated modules.

## Observability

Important failures and system decisions must eventually be visible.

---

# 20. Milestone Completion Rule

Every milestone follows:

```text
Design
 ↓
Tests
 ↓
Implementation
 ↓
Review
 ↓
Refactor
 ↓
Documentation
 ↓
Git Commit
 ↓
Milestone Complete
```

No milestone is considered complete merely because code exists.

---

# 21. Current Execution Plan

This is the sequence to follow from the current project state:

```text
[CURRENT]
M1/M2 — Domain + Market Observation Foundation
        ↓
M4 — Technical Analysis
        ↓
M5 — Fundamental Analysis
        ↓
M6 — Scoring
        ↓
M7 — Signal / Opportunity Detection
        ↓
M8 — Backtesting
        ↓
M11 — Reporting / Alerts
        ↓
RETURN TO M9 — Data Quality Rules
        ↓
M3 — Real Data Acquisition Integration
        ↓
M10 — Automation
        ↓
M12 — API / Dashboard
        ↓
M13 — Production Hardening
```

This sequence is deliberate. It is designed to reach the project's core business value before investing heavily in external-data reliability and operational infrastructure.

The exact order after the core analytical vertical may change after the core reveals new requirements. Such changes must be documented rather than made implicitly.

---

# 22. Changing the Roadmap

The roadmap may change when:

- requirements change
- an architectural assumption proves incorrect
- new evidence becomes available
- a dependency becomes unavailable
- a milestone reveals a better sequence

Changes affecting architecture or important domain decisions must be recorded in `docs/DECISION_LOG.md` or a dedicated DEC document.

---

# 23. Guiding Principle

> **Build the analytical brain first. Add the reliability, acquisition, automation, and interface layers around a core whose behavior is already understood.**
