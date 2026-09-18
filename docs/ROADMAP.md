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

M10 Automation is complete for its MVP scope. The execution, retry, idempotency, analysis integration, trigger, scheduler, and daily scheduling mechanics are implemented and documented.

The next milestone is M12 API & Dashboard.

The execution-order update is documented in `docs/DEC-047-EXECUTION-SEQUENCE-UPDATE.md`.

---

# 1. Purpose

This roadmap defines the planned evolution of the EGX Stock Analyzer from its domain foundation into an automated, explainable stock-analysis platform.

A milestone is complete only when its design, tests, implementation, review/refactor, documentation, Git commit, and acceptance criteria are satisfied.

The roadmap may change when new evidence or requirements justify a deliberate design decision.

---

# 2. Development Strategy

The project is developed through two connected tracks:

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

The analytical core was intentionally built before detailed data-quality and provider integration. Those reliability boundaries have now been implemented around the understood core.

The project still avoids premature UI, database-heavy architecture, AI-first architecture, microservices, and production-hardening concerns before their design gates are needed.

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
| M12 | API & Dashboard | 🟡 In Progress | Expose application capabilities through the API; runtime composition and a real-data vertical slice are validated on the integration branch |
| M13 | Production Hardening | 🔴 Not Started | Reliability, security, observability, deployment |

The milestone numbering is retained to preserve project history. The actual execution order is documented in `docs/DEC-047-EXECUTION-SEQUENCE-UPDATE.md`.

---

# 4. Current Execution Sequence

```text
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

```text
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

```text
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

```text
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

## Completed MVP

The M10 MVP includes:

- whole-market `Execution` lifecycle
- partial-failure handling with `COMPLETED_WITH_ERRORS`
- limited retry for explicitly retryable errors
- execution idempotency and recovery semantics
- stock-analysis pipeline integration
- daily-market analysis orchestration
- manual trigger
- scheduled trigger
- `Scheduler` protocol
- `InProcessScheduler`
- one-shot `run_at` timing
- due/not-due timing tests
- scheduled-trigger integration with the in-process scheduler
- `DailyAnalysisSchedule` application use case
- end-to-end daily scheduling integration

The scheduler boundary is:

```text
Scheduler
   │ WHEN
   ▼
ScheduledAnalysisTrigger
   │ WHAT
   ▼
DailyMarketAnalysis
   ▼
Execution
```

`DailyAnalysisSchedule` registers the existing analysis with a caller-provided `run_at`. It does not calculate market-calendar times.

See:

- `docs/DEC-048-M10-AUTOMATION-MVP.md`
- `docs/DEC-049-SCHEDULING-SEMANTICS-MVP.md`
- `docs/DEC-050-DAILY-ANALYSIS-SCHEDULE-MVP.md`
- `docs/DEC-051-DAILY-SCHEDULE-TIME-OWNERSHIP.md`
- `docs/M10-AUTOMATION-MVP-COMPLETION.md`

M10 is complete.

## Deferred

- recurring schedules
- cron expressions
- EGX trading calendar
- market-close calculation
- persistent schedules
- restart recovery
- distributed workers/queues
- Celery/Redis/RabbitMQ/Kubernetes
- advanced concurrency/scaling
- scheduler monitoring/dashboard

These require separate design gates.

---

# 9. M12 — API & Dashboard

## Status

M12 is **in progress**.

The current branch has validated the first API/runtime slice:

POST /api/v1/analysis/{symbol}
        ↓
StockCatalog
        ↓
RunStockAnalysisBySymbol
        ↓
RunStockAnalysis
        ↓
AnalysisInputAssembler
        ↓
Yahoo Finance market + annual fundamental data
        ↓
Data Quality
        ↓
DailyMarketAnalysis
        ↓
Execution
        ↓
AnalysisResultStore
        ↓
API response

Current validation includes:

- API composition through InfrastructureRuntime.
- Development stock catalog containing EGAL.
- Real EGAL market and annual fundamental data through Yahoo Finance.
- End-to-end integration test returning a successful analysis response.
- Execution failure diagnostics through DEC-062.
- Unit suite: 269 passed, 1 skipped, 1 deselected.
- Real-data integration: 1 passed.
- Dependency deprecation warnings remain as separate cleanup work.

These results establish the runtime/API foundation but do **not** mark M12 complete.

## Objective

Expose application capabilities to users.

API/UI must consume application/domain capabilities and must not own business rules.

---

## M12 Next Design Gate

The next M12 design work should define the API surface before adding more endpoints or dashboard behavior.

The gate should cover:

- Which application capabilities are exposed.
- Read vs command endpoints.
- Request/response DTO boundaries.
- HTTP status and error semantics.
- Symbol validation and unknown-symbol behavior.
- Analysis freshness/result retrieval semantics.
- How reports and alerts are exposed without moving business rules into FastAPI.
- Which dashboard concerns remain presentation-only.
- What remains explicitly deferred to M13.

No additional API surface should be treated as committed until this gate is documented.

## Current M12 Validation

The reporting and alert read-side API slice has now been locally validated:

- Focused API/application contract suite: **17 passed, 2 warnings**.
- Report endpoint preserves analysis date and Decimal transport serialization as strings.
- Alert endpoint preserves BUY-only domain semantics.
- Remaining warnings are dependency deprecations from Starlette/httpx and AnyIO; they are separate cleanup work and do not change the M12 business contract.

M12 remains **in progress**. Dashboard presentation boundary is now documented as a proposal in `docs/DEC-066-M12-DASHBOARD-PRESENTATION-BOUNDARY.md`. Dashboard presentation boundary is accepted, React + Vite is selected, and the first analysis-view frontend slice is now implemented. Local frontend build validation remains to be run.

# 10. M13 — Production Hardening

## Objective

Prepare the system for reliable long-term operation.

Areas include reliability, retries, failure recovery, idempotency, monitoring, secrets management, authentication/authorization, performance, caching, observability, deployment, backups, migrations, and rollback.

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

# 13. Changing the Roadmap

The roadmap may change when requirements change, an architectural assumption proves incorrect, new evidence becomes available, a dependency becomes unavailable, or a milestone reveals a better sequence.

Changes affecting architecture or important domain decisions must be recorded in `docs/DECISION_LOG.md` or a dedicated DEC document.

The current execution-order change is recorded in `docs/DEC-047-EXECUTION-SEQUENCE-UPDATE.md`.

---

# 14. Guiding Principle

> **Build the analytical brain first. Add the reliability, acquisition, automation, and interface layers around a core whose behavior is already understood.**
