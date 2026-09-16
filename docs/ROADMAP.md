# EGX Stock Analyzer — Roadmap

**Project:** EGX Stock Analyzer  
**Status:** Active  
**Master Plan:** This document is the project roadmap and the primary place to track planned execution order and current position.

---

# Current Position

The project has completed the current M5 Fundamental Analysis vertical slice and has entered M6 Scoring.

Completed analytical foundations include:

- Technical evidence composition
- Fundamental profitability evidence
- Fundamental liquidity evidence
- Fundamental revenue-growth evidence
- Fundamental analysis result/orchestration

Current M6 progress:

- Fundamental scoring MVP implemented
- Technical scoring MVP implemented
- Stock Quality Score MVP implemented
- Equal MVP contribution of `+1 / 0 / -1` per selected evidence area
- Explainable component scores
- No BUY/SELL decisions inside the scoring components

M7 has now progressed through:

- Entry Context MVP
- Entry Quality Score MVP
- Opportunity Classification MVP

Entry Context identifies the latest price and the nearest discovered structural support/resistance around it. Entry Quality measures the available structural context around the current price. Opportunity Classification now combines Stock Quality and Entry Quality using explicit MVP rules to produce BUY/WATCH/HOLD/AVOID.

Entry Context is documented in `docs/DEC-036-ENTRY-CONTEXT-MVP.md`.  
Entry Quality is documented in `docs/DEC-037-ENTRY-QUALITY-SCORE-MVP.md`.  
Opportunity Classification is documented in `docs/DEC-038-OPPORTUNITY-CLASSIFICATION-MVP.md`.

The project has not claimed a green full-suite test run in this session; test execution remains a local verification step.

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
| M4 | Technical Analysis | 🟢 Core Slice Built | Build deterministic technical evidence |
| M5 | Fundamental Analysis | 🟢 Core Slice Built | Build independent fundamental evidence |
| M6 | Scoring Engine | 🟡 In Progress | Combine evidence into explainable scores |
| M7 | Signal Generation | 🟡 In Progress | Establish entry context, entry quality, and opportunity classification |
| M8 | Backtesting | 🔴 Not Started | Validate analytical strategies historically |
| M9 | Data Quality | 🟡 Foundation Defined / Implementation Deferred | Implement real quality rules after the core analytical flow |
| M10 | Automation | 🔴 Not Started | Execute the analytical pipeline automatically |
| M11 | Reporting & Alerts | 🔴 Not Started | Deliver analytical results |
| M12 | API & Dashboard | 🔴 Not Started | Expose application capabilities |
| M13 | Production Hardening | 🔴 Not Started | Reliability, security, observability, deployment |

The milestone numbering is retained to preserve project history. The execution order deliberately builds the core analytical path before detailed Data Quality implementation.

---

# 4. Core Analytical Sequence

```text
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
M9 — Data Quality Rules
        ↓
M3 — Real Data Acquisition Integration
        ↓
M10 — Automation
        ↓
M12 — API / Dashboard
        ↓
M13 — Production Hardening
```

This sequence is deliberate. Changes to it require documentation rather than implicit route changes.

---

# 5. M6 — Scoring Engine

## Objective

Combine analytical evidence into consistent, explainable scores.

## Current Vertical Slices

### Fundamental Score

```text
Profitability   +1 / 0 / -1
Liquidity       +1 / 0 / -1
Revenue Growth  +1 / 0 / -1
```

Undefined or insufficient evidence contributes zero.

The Fundamental Score ranges from `-3` to `+3` and preserves component contributions for explainability.

See `docs/DEC-033-FUNDAMENTAL-SCORING-MVP.md`.

### Technical Score

```text
Trend       +1 / 0 / -1
Momentum    +1 / 0 / -1
Volume      +1 / 0 / -1
```

Undefined or insufficient evidence contributes zero.

The Technical Score ranges from `-3` to `+3` and preserves component contributions for explainability.

Support / Resistance is intentionally excluded from this score and reserved for the future Entry Quality concern.

See `docs/DEC-034-TECHNICAL-SCORING-MVP.md`.

### Stock Quality Score

```text
Fundamental Score  -3..+3
        +
Technical Score    -3..+3
        ↓
Stock Quality      -6..+6
```

The combined score preserves both component scores and performs no additional weighting or normalization.

See `docs/DEC-035-STOCK-QUALITY-SCORE-MVP.md`.

## Deferred

- configurable weighting
- normalized 0–100 opportunity score
- Entry Quality scoring
- BUY/SELL decisions
- ranking
- strategy-specific scoring policies

These require later design decisions and are not silently introduced into the MVP.

---

# 6. M7 — Signal Generation

## Objective

Transform analytical evidence and scores into actionable classifications.

### Entry Context

The first M7 slice establishes structural context around the latest market price.

```text
Latest Close
    ↓
Current Price
    ↓
Nearest Support Below
Nearest Resistance Above
```

This is context only. It does not assign a trading decision.

See `docs/DEC-036-ENTRY-CONTEXT-MVP.md`.

### Entry Quality Score

The current MVP evaluates the availability of nearest structural support and resistance around the current price.

```text
Support Context      +1 / 0
Resistance Context   +1 / 0
        ↓
Entry Quality        0..+2
```

The score is intentionally not a probability, expected return, or BUY/SELL signal. It does not use arbitrary proximity thresholds or level-strength assumptions.

See `docs/DEC-037-ENTRY-QUALITY-SCORE-MVP.md`.

### Opportunity Classification

The MVP combines Stock Quality and Entry Quality through explicit rules:

```text
Strong negative quality  → AVOID
Strong quality + entry   → BUY
Positive quality         → WATCH
Other combinations       → HOLD
```

The exact thresholds and precedence are recorded in `docs/DEC-038-OPPORTUNITY-CLASSIFICATION-MVP.md`.

This classification is an analytical state, not a probability, expected return, or guarantee of future price movement.

## M7 Completion Gate

M7 remains pending final local verification and review/refactor acceptance.

The next major milestone after M7 is M8 Backtesting.

---

# 7. M8 — Backtesting

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

The M8 design gate must explicitly define the backtest model before implementation, including signal timing, execution timing, position lifecycle, transaction costs, and evaluation metrics.

---

# 8. M9 — Data Quality

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

# 9. M3 — Data Acquisition

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

# 10. M10 — Automation

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

---

# 11. M11 — Reporting & Alerts

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

---

# 12. M12 — API & Dashboard

## Objective

Expose application capabilities to users.

API/UI must consume application/domain capabilities and must not own business rules.

---

# 13. M13 — Production Hardening

## Objective

Prepare the system for reliable long-term operation.

Areas include reliability, retries, failure recovery, idempotency, monitoring, secrets management, authentication/authorization, performance, caching, observability, deployment, backups, migrations, and rollback.

---

# 14. Cross-Cutting Requirements

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

# 15. Milestone Completion Rule

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

# 16. Changing the Roadmap

The roadmap may change when requirements change, an architectural assumption proves incorrect, new evidence becomes available, a dependency becomes unavailable, or a milestone reveals a better sequence.

Changes affecting architecture or important domain decisions must be recorded in `docs/DECISION_LOG.md` or a dedicated DEC document.

---

# 17. Guiding Principle

> **Build the analytical brain first. Add the reliability, acquisition, automation, and interface layers around a core whose behavior is already understood.**
