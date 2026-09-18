# EGX Stock Analyzer — Roadmap

**Project:** EGX Stock Analyzer  
**Status:** Active  
**Master Plan:** This document is the project roadmap and the primary place to track planned execution order and current position.

---

# Current Position

The project has completed the core analytical path through M8 and the reliability/acquisition slices needed to validate real market data through the domain boundary.

Completed analytical foundations include:

- Technical evidence composition
- Fundamental analysis and orchestration
- Fundamental scoring
- Technical scoring
- Stock Quality Score
- Entry Context
- Entry Quality Score
- Opportunity Classification
- Backtesting MVP
- Reporting & Alerts MVP

Completed reliability/acquisition foundations include:

- Raw market observations
- Data Quality Assessment
- Raw observation → validated PriceBar conversion
- Provider-neutral market-data acquisition boundary
- Yahoo Finance development adapter
- Live COMI acquisition-to-PriceBar smoke validation
- Execution orchestration
- Manual analysis trigger
- Scheduled analysis trigger
- In-process one-shot scheduler
- Daily analysis scheduling use case
- End-to-end scheduled analysis integration

M10 Automation is complete for its MVP scope.

M11 Reporting & Alerts is complete for its MVP scope.

M12 has established and validated its first API/runtime/dashboard presentation slice on the integration branch. The branch is protected by CI covering Python unit tests plus frontend tests and production build. The first dashboard slice is now frozen under `docs/DECISION_LOG.md` DEC-069; further dashboard capabilities require a new design gate.

The execution-order update is documented in `docs/DEC-047-EXECUTION-SEQUENCE-UPDATE.md`.

---

# 1. Purpose

This roadmap defines the planned evolution of the EGX Stock Analyzer from its domain foundation into an automated, explainable stock-analysis platform.

A milestone is complete only when its design, tests, implementation, review/refactor, documentation, Git commit, and acceptance criteria are satisfied.

The roadmap may change when new evidence or requirements justify a deliberate design decision.

---

# 2. Development Strategy

The project is developed through two connected tracks:

```
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

The analytical core was intentionally built before detailed data-quality and provider integration. Those reliability boundaries have now been implemented around the understood core.

The project still avoids premature database-heavy architecture, AI-first architecture, microservices, and production-hardening concerns before their design gates are needed.

---

# 3. Milestone Overview

| Milestone | Name | Status | Current Intent |
|---|---|---|---|
| M0 | Vision & Blueprint | 🟡 In Progress | Keep project direction and engineering method explicit |
| M1 | Domain Foundation | 🟢 Foundation Built | Establish stable core domain concepts |
| M2 | Market Data Foundation | 🟢 Foundation Built | Establish market observation semantics |
| M3 | Data Acquisition | 🟢 Complete | Acquire external observations through a replaceable provider boundary |
| M4 | Technical Analysis | 🟢 Core Slice Built | Build deterministic technical evidence |
| M5 | Fundamental Analysis | 🟢 Core Slice Built | Build independent fundamental evidence |
| M6 | Scoring Engine | 🟢 Core Slice Built | Combine evidence into explainable scores |
| M7 | Opportunity Detection | 🟢 Complete | Establish entry context, entry quality, and opportunity classification |
| M8 | Backtesting | 🟢 Complete | Evaluate current classification historically |
| M9 | Data Quality | 🟢 Complete | Assess raw observations and gate PriceBar creation |
| M10 | Automation | 🟢 Complete | Execute the analytical pipeline automatically |
| M11 | Reporting & Alerts | 🟢 Complete | Produce immutable reports and alert candidates |
| M12 | API & Dashboard | 🟢 First Slice Complete | Freeze and validate the first user-facing API/runtime/dashboard slice |
| M13 | Production Hardening | 🟢 Operational Baseline + Persistence MVP Complete | Establish production boundaries; further hardening requires separate design gates |

The milestone numbering is retained to preserve project history. The actual execution order is documented in `docs/DEC-047-EXECUTION-SEQUENCE-UPDATE.md`.

---

# 4. Current Execution Sequence

```
M4 — Technical Analysis
        ↓
M5 — Fundamental Analysis
        ↓
M6 — Scoring
        ↓
M7 — Opportunity Detection
        ↓
M8 — Backtesting
        ↓
M11 — Reporting / Alerts
        ↓
M9 — Data Quality
        ↓
M3 — Data Acquisition
        ↓
M10 — Automation
        ↓
M12 — API / Dashboard
        ↓
M13 — Production Hardening
```

This sequence reflects completed work and is now documented rather than treated as an implicit route change.

---

# 5. Completed Core Analytical Milestones

M4 through M8 established deterministic, explainable analytical behavior, including technical and fundamental evidence, scoring, opportunity classification, and historical evaluation.

The accepted design documents remain the source of truth for the individual MVP contracts:

- `docs/DEC-033-FUNDAMENTAL-SCORING-MVP.md`
- `docs/DEC-034-TECHNICAL-SCORING-MVP.md`
- `docs/DEC-035-STOCK-QUALITY-SCORE-MVP.md`
- `docs/DEC-036-ENTRY-CONTEXT-MVP.md`
- `docs/DEC-037-ENTRY-QUALITY-SCORE-MVP.md`
- `docs/DEC-038-OPPORTUNITY-CLASSIFICATION-MVP.md`
- `docs/DEC-039-BACKTESTING-MVP.md`
- `docs/DEC-041-REPORTING-ALERTS-MVP.md`

---

# 6. M9 — Data Quality

## Objective

Assess whether raw external observations are usable for analysis.

## Implemented Boundary

```
RawPriceBarObservation
        ↓
DataQualityAssessor
        ↓
DataQualityAssessment
        ↓
VALID → PriceBarFactory → PriceBar
INVALID / SUSPECT / UNKNOWN → not converted
```

The MVP preserves raw observations and does not silently repair invalid external data.

See `docs/DEC-042-DATA-QUALITY-ASSESSOR-MVP.md` and `docs/DEC-043-RAW-OBSERVATION-TO-PRICE-BAR.md`.

M9 is complete.

---

# 7. M3 — Data Acquisition

## Objective

Connect external market-data providers without leaking provider-specific behavior into the core domain.

## Implemented

```
Application
    ↓
MarketDataProvider
    ↓
Provider Adapter
    ↓
RawPriceBarObservation
    ↓
Data Quality
    ↓
PriceBar
    ↓
Analysis
```

Yahoo Finance is currently implemented as a development adapter behind the provider boundary.

The live COMI smoke test validates the real acquisition path. It intentionally allows external observations to be invalid; Data Quality must identify and reject them rather than weakening the domain rules.

See:

- `docs/DEC-044-DATA-ACQUISITION-BOUNDARY-MVP.md`
- `docs/DEC-045-YAHOO-FINANCE-ADAPTER-MVP.md`
- `docs/DEC-046-YAHOO-DAILY-TIMESTAMP-NORMALIZATION.md`
- `docs/M3-DATA-ACQUISITION-MVP-COMPLETION.md`

M3 is complete.

---

# 8. M10 — Automation

## Objective

Run the analytical pipeline automatically.

Target flow:

```
Collect
  ↓
Assess Data Quality
  ↓
Analyze
  ↓
Score
  ↓
Detect Opportunities
  ↓
Generate Report
  ↓
Send Alerts
```

M10 MVP is complete.

Deferred scheduler capabilities remain:

- recurring schedules
- cron expressions
- EGX trading calendar
- market-close calculation
- persistent schedules
- restart recovery
- distributed workers/queues
- advanced concurrency/scaling
- scheduler monitoring/dashboard

These require separate design gates.

---

# 9. M12 — API & Dashboard

## Status

M12 first slice is **complete**. Further dashboard capabilities are deferred behind new design gates.

The first API/runtime slice is implemented and validated through the integration branch.

### Runtime boundary

```
InfrastructureRuntime
        ↓
StockAnalysisRuntime
        ↓
Application capabilities
        ↓
AnalysisResultStore
```

### API surface

```
GET  /api/v1/analysis/{symbol}
POST /api/v1/analysis/{symbol}

GET  /api/v1/reports/{symbol}
GET  /api/v1/alerts/{symbol}
```

The report and alert endpoints are read-side projections of completed analysis. FastAPI owns transport concerns only.

### Dashboard boundary

```
React + Vite Dashboard
          ↓ HTTP
        FastAPI
          ↓
    Application
          ↓
       Domain
          ↓
   Infrastructure
```

The first dashboard view consumes report/alert read models and does not calculate analytical values.

### Current validation

GitHub Actions Run #95 on commit `bdc1799` completed successfully with:

- Python unit-tests job: **success**
- Frontend tests job: **success**
- Frontend production build: **success**

The frontend suite currently contains API-client and dashboard component coverage. The latest validated frontend test run is **7 tests passing across 2 test files**.

The Python CI job successfully installs the project package and executes the non-integration test suite.

A real-data EGAL integration test validates the current Yahoo Finance market + annual fundamental data path. The integration slice now also verifies that a successful analysis is readable through the Report endpoint and that the Alert endpoint returns either a BUY candidate or the expected no-candidate 404.

Dependency deprecation warnings remain a separate compatibility cleanup concern and do not change the current business contracts.

### M12 design decisions already accepted

- `DEC-063` — first API surface and boundary
- `DEC-064` — reporting/alerts API boundary
- `DEC-066` — API price values are JSON numbers
- `DEC-067` — React + Vite frontend technology
- `DEC-068` — dashboard presentation boundary

The dashboard presentation boundary is documented in `docs/DEC-068-M12-DASHBOARD-PRESENTATION-BOUNDARY.md`.

### Remaining M12 work

The first M12 slice is complete. M12 should not be expanded opportunistically.

Before adding additional endpoints or advanced dashboard behavior, a new design gate should define the next user-facing capability and its API contract. See DEC-069 for the scope freeze.

Potential deferred capabilities include:

- market-wide ranking
- watchlists
- historical comparison
- interactive charting
- notification configuration
- authentication/authorization
- real-time streaming
- advanced filtering
- automated trading

These are not part of the current first dashboard slice.

---

# 10. M13 — Production Hardening

## Objective

Prepare the system for reliable long-term operation.

Areas include reliability, retries, failure recovery, idempotency, monitoring, secrets management, authentication/authorization, performance, caching, observability, deployment, backups, migrations, and rollback.

M13's first Operational Runtime Baseline is complete under DEC-070: health exposure, safe execution errors, application lifecycle verification, idempotent runtime shutdown, and CI coverage are validated. The current configuration contract has no required external settings, so no artificial validation rule was introduced. DEC-071 established the durable analysis-state boundary, and DEC-072 accepted SQLite plus an explicit versioned serializer as the first persistence MVP. The persistence implementation is now validated through store-level and API-level tests, including analysis → SQLite → store recreation → report/alert projections. The API/report/dashboard contracts remain unchanged.

---

# 11. Cross-Cutting Requirements

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

# 12. Milestone Completion Rule

Every milestone follows:

```
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

# 13. Changing the Roadmap

The roadmap may change when requirements change, an architectural assumption proves incorrect, new evidence becomes available, a dependency becomes unavailable, or a milestone reveals a better sequence.

Changes affecting architecture or important domain decisions must be recorded in `docs/DECISION_LOG.md` or a dedicated DEC document.

The current execution-order change is recorded in `docs/DEC-047-EXECUTION-SEQUENCE-UPDATE.md`.

---

# 14. Guiding Principle

> **Build the analytical brain first. Add the reliability, acquisition, automation, and interface layers around a core whose behavior is already understood.**
