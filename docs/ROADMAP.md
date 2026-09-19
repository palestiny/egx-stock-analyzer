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
| M14 | Market-Wide Analysis | 🟢 Complete | Sequential market-wide orchestration merged and validated by GitHub Actions Run #200 on implementation head |
| M15 | Market Opportunity Ranking | 🟢 Complete | Deterministic BUY/WATCH ranking over completed stock-analysis results |
| M16 | Market Opportunity View | 🟢 Complete | Read stored results, reuse M15 ranking, and expose the ordered opportunity set through API/dashboard |
| M17 | Market Universe & All-Market Execution | 🟢 Complete | Discover the configured universe through StockCatalog and execute it through the existing market-wide capability |
| M18 | Scheduled Full-Market Analysis | 🟢 Complete | One-shot scheduling adapter for configured-market execution; no scheduling business logic moved into the scheduler |
| M19 | Recurring Market Scheduling | 🟢 Complete | Deterministic daily recurring full-market scheduling capability with explicit calendar/timezone/idempotency semantics |
| M20 | Historical Analysis Result History | 🟢 Complete | Preserve immutable completed analytical snapshots across recurring runs while keeping latest-result compatibility |
| M21 | Historical Analysis View | 🟢 Complete | Expose stored historical analysis snapshots through a read-only application/API/dashboard boundary |
| M22 | Historical Analysis Comparison | 🟢 Complete | Compare two persisted snapshots by UUID through a read-only application/API/dashboard boundary |
| M23 | Historical Performance Analytics | 🟢 Complete | Calculate and present descriptive price-change metrics between two persisted snapshots without predicting future performance |
| M24 | Historical Analysis Change Detection | 🟢 Complete | Detect descriptive changes between two persisted analysis snapshots through a reusable read-side capability |
| M25 | Alert Delivery & Notification Boundary | 🟢 Complete | Deliver existing alert candidates through a provider-neutral, durable, idempotent synchronous boundary |
| M26 | External Notification Provider Integration | 🟢 Complete | Integrate Telegram as the first concrete provider behind the M25 notification boundary |
| M27 | Alert Delivery Trigger & Transport Boundary | 🟢 Complete | Explicitly deliver an existing alert candidate through the provider-neutral delivery boundary |
| M28 | Automatic Alert Delivery Policy | 🟢 Complete | Automatically deliver existing eligible alert candidates after completed analysis without coupling delivery to analytical execution |
| M29 | Scheduled Automatic Alert Delivery | 🟢 Complete | Connect recurring full-market analysis to the existing automatic-delivery capability through an explicit workflow boundary |
| M30 | Durable Scheduled Workflow | 🟢 Complete | Persist scheduled workflow lifecycle, integrate recurring occurrences, and detect interrupted executions without introducing distributed execution |
| M31 | Durable Workflow Recovery | 🟢 Complete | Explicitly recover one interrupted scheduled workflow occurrence using existing workflow and idempotency boundaries |
| M32 | Automatic Scheduled Workflow Resume | 🟢 Complete | Automatically recover eligible interrupted scheduled workflow executions during application startup |
| M33 | Scheduled Workflow Operational Visibility | 🟢 Complete | Provide a provider-neutral read-side capability over persisted scheduled workflow executions |
| M34 | Scheduled Workflow Operational Visibility API | 🟢 Complete | Expose the M33 read model through a read-only HTTP boundary |
| M35 | Scheduled Workflow Operational Dashboard | 🟢 Complete | Present scheduled workflow operational state through the existing React dashboard |
| M36 | Scheduled Workflow Recovery Control | 🟢 Complete | Explicit operator-triggered recovery of one INTERRUPTED scheduled workflow execution through API and dashboard |
| M37 | Authentication & Authorization Boundary | 🟢 Complete | Protect all non-health application endpoints with a single-operator bearer-token boundary; defer multi-user identity and ownership |
| M38 | Multi-User Identity & Ownership | 🟢 Persistence + Capability Ownership Slice Complete | Persist application users, migrate ScheduledWorkflowExecution ownership, preserve legacy system/global records, and validate ownership across restart |
| M39 | Multi-User Authentication & Identity Transport | 🟢 Complete | Configured multi-user bearer authentication with lifecycle validation and ownership-scoped scheduled workflow read/recovery |
| M40 | Frontend Authentication & Session UX | 🟢 Complete | Durable user credential lifecycle and browser session UX over the existing identity/ownership boundary |
| M41 | User Management & Credential Administration | 🟢 Complete | Operator user lifecycle administration, self-service durable credential rotation, audit boundary, API, and dashboard controls |
| M42 | Management Audit Reporting | 🟢 Complete | Define a read-only, operator-controlled audit reporting capability over the M41 durable management-audit boundary |
| M43 | User-Facing Audit History | 🟢 Complete | Add controlled authenticated-user visibility over the durable management-audit boundary |
| M44 | Execution Reliability & History | 🟢 Complete | Harden durable workflow idempotency, concurrent claiming, optimistic revisions, lifecycle history, and atomic state/history persistence |
| M45 | Scheduled Workflow Lifecycle History Visibility | 🟢 Complete | Expose one execution's persisted lifecycle history through read-only application/API/dashboard boundaries |
| M46 | Scheduled Workflow History Query Extensions | 🟢 Complete | Optional bounded sequence-cursor pagination with M45 complete-history compatibility |
| M47 | Scheduled Workflow History Filtering | 🟡 Design Accepted | Typed lifecycle-state filtering over the existing paginated history read boundary |
| M47 | Scheduled Workflow History Filtering | 🟡 Design Proposed | Evaluate typed lifecycle-state filtering over the existing paginated history read boundary |


M47 design is **accepted** in `docs/DEC-108-M47-SCHEDULED-WORKFLOW-HISTORY-FILTERING-DESIGN-GATE.md`. Implementation is the next controlled step.

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
        ↓
M14 — Market-Wide Analysis
        ↓
M15 — Market Opportunity Ranking
        ↓
M16 — Market Opportunity View
        ↓
M17 — Market Universe & All-Market Execution
        ↓
M18 — Scheduled Full-Market Analysis
        ↓
M19 — Recurring Market Scheduling
        ↓
M20 — Historical Analysis Result History
        ↓
M21 — Historical Analysis View
        ↓
M22 — Historical Analysis Comparison
        ↓
M23 — Historical Performance Analytics
        ↓
M24 — Historical Analysis Change Detection
        ↓
M25 — Alert Delivery & Notification Boundary
        ↓
M26 — External Notification Provider Integration
        ↓
M27 — Alert Delivery Trigger & Transport Boundary
        ↓
M28 — Automatic Alert Delivery Policy
        ↓
M29 — Scheduled Automatic Alert Delivery
        ↓
M30 — Durable Scheduled Workflow
        ↓
M31 — Durable Workflow Recovery
        ↓
M32 — Automatic Scheduled Workflow Resume
        ↓
M33 — Scheduled Workflow Operational Visibility
        ↓
M34 — Scheduled Workflow Operational Visibility API
        ↓
M35 — Scheduled Workflow Operational Dashboard
        ↓
M36 — Scheduled Workflow Recovery Control
        ↓
M37 — Authentication & Authorization Boundary
        ↓
M38 — Multi-User Identity & Ownership
        ↓
M39 — Multi-User Authentication & Identity Transport
        ↓
M40 — Frontend Authentication & Session UX
        ↓
M41 — User Management & Credential Administration
        ↓
M42 — Management Audit Reporting
        ↓
M43 — User-Facing Audit History
        ↓
M44 — Execution Reliability & History
        ↓
M45 — Scheduled Workflow Lifecycle History Visibility
        ↓
M46 — Scheduled Workflow History Query Extensions
        ↓
M47 — Scheduled Workflow History Filtering
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

GitHub Actions Run #171 on commit `c385c1d7` completed successfully with:

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

M13's first Operational Runtime Baseline is complete under DEC-070: health exposure, safe execution errors, application lifecycle verification, idempotent runtime shutdown, and CI coverage are validated. The current configuration contract has no required external settings, so no artificial validation rule was introduced. DEC-071 established the durable analysis-state boundary, and DEC-072 accepted SQLite plus an explicit versioned serializer as the first persistence MVP. The persistence implementation is now validated through store-level and API-level tests, including analysis → SQLite → store recreation → report/alert projections. The API/report/dashboard contracts remain unchanged. The latest externally observed successful CI validation is Run #171 on commit `c385c1d7`. Subsequent documentation-only commits are present on the integration branch, but their workflow runs are not currently observable through the available GitHub workflow-run integration; therefore they are not marked as independently CI-validated here. A read-only SQLite inspection command is available for local diagnostics.

---

# 11. M14 — Market-Wide Analysis

## Status

The M14 design gate is **accepted** in `docs/DEC-073-M14-MARKET-WIDE-ANALYSIS-DESIGN-GATE.md`. The implementation was merged through PR #3. GitHub Actions Run #200 completed successfully for implementation head `df6f0b93d51639e49c65a46a6d39ffac35850294`, providing the repository-level CI validation for the M14 implementation.

### Accepted application boundary

```
RunMarketAnalysis
      ↓
StockCatalog
      ↓
RunStockAnalysis
      ↓
AnalysisResultStore
```

The MVP accepts an explicit ordered symbol list, executes sequentially, preserves successful per-stock persistence through the existing single-stock capability, and returns an aggregate state of `COMPLETED`, `COMPLETED_WITH_ERRORS`, or `FAILED`. An empty universe is a completed no-op. Unknown symbols are individual failures, while duplicate normalized symbols are invalid input.

The merged implementation includes focused TDD coverage for empty input, success, ordering, partial failure, all-failure, unknown symbols, duplicate input, persistence preservation, and execution identity, plus runtime wiring coverage.

The aggregate run reuses the existing `Execution` aggregate and its `Execution.id`; M14 does not add aggregate persistence. Per-stock retry remains inside the existing single-stock capability.

Deferred from M14: ranking, watchlists, history, concurrency, distributed execution, notification delivery, dashboard changes, trading decisions, portfolio allocation, provider failover, and AI-based selection.

---

# 37. M37 — Authentication & Authorization Boundary

## Status

M37 is **complete**. The accepted design in `docs/DEC-096-M37-AUTHENTICATION-AUTHORIZATION-DESIGN-GATE.md` has been implemented and merged to `main` through PR #70. GitHub Actions Run #1159 passed on implementation head `d160b916` before merge.

### Accepted security boundary

```
HTTP
  ↓
Bearer Token Authentication Adapter
  ↓
AuthenticatedIdentity(operator)
  ↓
Authorization Boundary
  ↓
Application Capability
  ↓
Domain
```

`GET /health` remains public. All other application/API endpoints are protected by a configured bearer operator token. The MVP uses one operator permission and does not introduce users, password storage, sessions, external identity providers, ownership, or permission administration.

Authentication failures use HTTP 401; authenticated callers lacking the required operator permission use HTTP 403. The token is configuration-only, never persisted, logged, or returned.

Multi-user identity and ownership remain future design gates.

---

# 38. M38 — Multi-User Identity & Ownership

## Status

M38 persistence/capability migration is **complete** for the accepted DEC-098 slice.

The implementation was merged through PR #76 at merge commit `aa102e4b87c197882ed329fe085601a2be8d7e62`. GitHub Actions Run #1294 completed successfully for implementation head `77f05c1eebf99226b2ac464e87d5c0d4dce09068`, with both the Python unit-tests and frontend-tests jobs successful.

### Implemented boundary

```
Authentication Adapter
        ↓
AuthenticatedIdentity
        ↓
Ownership Authorization Boundary
        ↓
ScheduledWorkflowExecution
        ↓
UserStore + ScheduledWorkflowExecutionStore
        ↓
SQLite
```

### Completed behavior

- dedicated `UserStore` persistence on the existing SQLite deployment;
- deterministic legacy operator identity bootstrap;
- immutable user lifecycle persistence/reload;
- nullable `owner_user_id` on `ScheduledWorkflowExecution`;
- explicit distinction between user-owned and system/global legacy workflow executions;
- ownership persistence across repository/application restart;
- ownership checks for user-owned workflow execution operations;
- legacy operator compatibility limited to system/global records;
- schema migration for existing workflow tables without silently assigning historical ownership;
- deterministic ownership-isolation and persistence tests.

M38 does not add passwords, sessions, external identity providers, organizations, roles, delegated access, or bulk historical ownership migration.

### Completion boundary

The accepted M38 work establishes durable identity and one concrete ownership proof. It does **not** imply that the product is now a general-purpose multi-user management system or that every existing resource has been migrated to user ownership.

The next capability requires a new design gate rather than expanding M38 opportunistically.

---

---

# 12. M15 — Market Opportunity Ranking

## Status

M15 is **complete**. The accepted contract is documented in `docs/DEC-074-M15-MARKET-OPPORTUNITY-RANKING-DESIGN-GATE.md`, and the implementation was merged through PR #8.

### Accepted application boundary

```
Market Analysis
      ↓
Completed StockAnalysisResult set
      ↓
RankMarketOpportunities
      ↓
Ordered Opportunity Set
```

The MVP ranks only BUY and WATCH results. Ordering is deterministic by:

1. Stock Quality score descending
2. Entry Quality score descending
3. Technical score descending
4. Fundamental score descending
5. normalized symbol ascending

HOLD and AVOID results are excluded without synthetic scores. Duplicate normalized symbols are rejected. Source analytical results are preserved without mutation, and the ranking capability does not persist or recalculate analytical values.

GitHub Actions Run #244 completed successfully for implementation head `6ff1d01d63b8e4663c6279ff3b12f236540b30c9`. A subsequent documentation-only correction removed a stale duplicate "Proposed" status from DEC-074 before PR #8 was merged.

Deferred from M15: API/dashboard integration, historical ranking persistence, personalized ranking, portfolio allocation, position sizing, trading execution, AI ranking, and changes to stock-level scoring/classification.

---


# 13. M16 — Market Opportunity View

## Status

M16 is **complete**. The accepted contract is documented in `docs/DEC-075-M16-MARKET-OPPORTUNITY-VIEW-DESIGN-GATE.md`, and the implementation was merged through PR #12.

### Accepted application boundary

```
HTTP
  ↓
GetMarketOpportunityRanking
  ↓
AnalysisResultStore
  ↓
RankMarketOpportunities
  ↓
Ordered Opportunity Read Model
  ↓
HTTP / Dashboard
```

The capability accepts an explicit ordered symbol list, normalizes and validates it, reads the latest stored result for each symbol, reports missing symbols explicitly, and delegates ordering to the existing M15 ranking capability. It never executes fresh analysis and introduces no persistence schema.

The API exposes `GET /api/v1/opportunities?symbols=...`, while the React dashboard renders the ordered opportunity rows and missing-result state without duplicating ranking or analytical logic.

GitHub Actions Run #281 completed successfully for implementation head `ac3d0dff1348952c55e129dc03d8fcc4962579ea` before PR #12 was merged.

Deferred from M16: watchlist persistence, historical ranking, personalized ranking, portfolio allocation, position sizing, automated trading, real-time streaming, analysis-on-demand from the opportunity endpoint, and AI ranking.

---

# 14. M17 — Market Universe & All-Market Execution

## Status

The M17 design gate is **accepted** in `docs/DEC-076-M17-MARKET-UNIVERSE-EXECUTION-DESIGN-GATE.md`, and the implementation is complete.

### Accepted application boundary

RunConfiguredMarketAnalysis
          ↓
StockCatalog.symbols()
          ↓
RunMarketAnalysis
          ↓
RunStockAnalysis
          ↓
AnalysisResultStore

M17 extends the existing StockCatalog with deterministic symbol enumeration and introduces a configured-market execution capability. The HTTP command endpoint is POST /api/v1/market-analysis. The scheduler remains a trigger only, and no new persistence, ranking, dashboard logic, or concurrency is introduced.

PR #15 was merged into `main` after GitHub Actions Run #349 completed successfully for implementation head `b5b420923490109ccb8307c2ce00b32691d06f6a`. The completion record is `docs/M17-MARKET-UNIVERSE-EXECUTION-MVP-COMPLETION.md`.

M17 is complete for its accepted MVP scope. The next capability requires a new design gate.

---

# 15. M18 — Scheduled Full-Market Analysis

## Status

The M18 design gate is **accepted** in `docs/DEC-077-M18-SCHEDULED-FULL-MARKET-ANALYSIS-DESIGN-GATE.md`, and the implementation is complete through PR #20. The one-shot scheduling trigger was merged into `main` as commit `08c0e167384875dda59ed93dfa88cd753f2389cd`. GitHub Actions status for this commit was not observable through the available workflow-run integration at the time of completion.

### Accepted boundary

```
Scheduler
    ↓
ScheduledConfiguredMarketAnalysis
    ↓
RunConfiguredMarketAnalysis
    ↓
StockCatalog.symbols()
    ↓
RunMarketAnalysis
    ↓
RunStockAnalysis
    ↓
AnalysisResultStore
```

M18 is a one-shot scheduling adapter. The configured universe is resolved at execution time, the execution date is determined at execution time, and no recurring schedule, persistence, trading-calendar, concurrency, or scheduling API behavior is introduced.

---

# 16. M19 — Recurring Market Scheduling

## Status

The M19 design gate is **accepted** in docs/DEC-078-M19-RECURRING-MARKET-SCHEDULING-DESIGN-GATE.md, and the implementation is complete through PR #22.

M19 uses daily-at-local-time recurrence, Africa/Cairo as the default timezone, Monday-Friday as the temporary calendar policy, skipped missed occurrences, no concurrent market-analysis execution, process-local occurrence idempotency, process-local schedules, an injected clock, and continuation after failed occurrences.

GitHub Actions Run #404 validated implementation head a9ab32752bc03f6564cd47e820c96c9cad522185: Python unit tests and frontend tests/build all passed.

The existing RunConfiguredMarketAnalysis capability remains the business-execution boundary. The scheduler remains timing-only.

Completion record: docs/M19-RECURRING-MARKET-SCHEDULING-MVP-COMPLETION.md.

---

# 17. M20 — Historical Analysis Result History

## Status

The design gate is **accepted** in `docs/DEC-079-M20-HISTORICAL-ANALYSIS-RESULT-HISTORY-DESIGN-GATE.md`. Implementation is now authorized for the defined MVP.

The problem is now concrete: M19 can execute the market repeatedly, while the current analysis result persistence is latest-result-only. This prevents persisted comparison of completed analysis snapshots across recurring runs.

The MVP uses append-only snapshot history behind `AnalysisResultStore`, preserves the existing `get(symbol)` latest-result contract, derives latest from history, migrates the existing latest-only row, and defers HTTP/dashboard history exposure to a separate gate.

### Accepted boundary

```
Analysis / Scheduled Execution
          ↓
AnalysisResultStore
          ↓
Historical Analysis Result Repository
          ↓
SQLite
```

### Accepted outcome

Preserve immutable completed analysis snapshots while keeping the current latest-result read contract compatible.

### Explicitly deferred

Historical market-data warehousing, historical ranking, performance analytics, change-detection rules, notifications, watchlists, portfolio/trading behavior, AI analysis, and API/dashboard history exposure remain deferred.

---

# 18. M20 — Historical Analysis Result History

## Status

M20 is **complete**. The accepted design is documented in `docs/DEC-079-M20-HISTORICAL-ANALYSIS-RESULT-HISTORY-DESIGN-GATE.md`, and the implementation was merged through PR #24.

GitHub Actions Run #430 completed successfully for implementation fix head `1a8f72eaeeec57306e9dcdc1f4de113863f13eac`, validating the Python unit tests and frontend tests/build workflow.

### Accepted outcome

The system now preserves immutable completed analysis snapshots in history while keeping the existing latest-result `get(symbol)` compatibility path. SQLite migration preserves an existing latest-only row as one historical snapshot, and deterministic history queries support optional date bounds.

Failed analyses do not create successful snapshots. Historical reads never execute fresh analysis, and persistence/serialization errors remain explicit.

### Scope boundary

Historical HTTP/dashboard exposure, historical ranking, performance analytics, market-data warehousing, change detection, notifications, watchlists, portfolio/trading behavior, distributed storage, and AI analysis remain deferred behind separate design gates.

---

# 20. M21 — Historical Analysis View

## Status

M21 is **complete**. The accepted design is documented in `docs/DEC-080-M21-HISTORICAL-ANALYSIS-VIEW-DESIGN-GATE.md`, and the implementation was merged through PR #28.

GitHub Actions Run #484 completed successfully for implementation head `4f2d047461b2ffa5e05d3cdc4d22cdee3f0e6eb9`, validating the Python unit tests and frontend tests/build workflow.

### Accepted boundary

```
Dashboard
    ↓
HTTP
    ↓
GetAnalysisHistory
    ↓
AnalysisResultStore
    ↓
SQLite History
```

M21 exposes `GET /api/v1/history/{symbol}` with inclusive optional date bounds. Unknown symbols return 404, while known symbols with no stored history return an empty collection. The endpoint never triggers fresh analysis.

The dashboard now renders the deterministic newest-first historical snapshot list with loading, empty, and history-error states. It consumes the API read model and does not calculate or mutate analytical values.

### Scope boundary

Historical ranking, performance analytics, change detection, OHLC charting, notifications, watchlists, portfolio/trading behavior, pagination, authentication/authorization, and AI analysis remain deferred behind separate design gates.

Completion record: `docs/M21-HISTORICAL-ANALYSIS-VIEW-MVP-COMPLETION.md`.

---

# 21. M22 — Historical Analysis Comparison

## Status

M22 is **complete**. The accepted design is documented in `docs/DEC-081-M22-HISTORICAL-ANALYSIS-COMPARISON-DESIGN-GATE.md`, and the implementation was merged through PR #30. GitHub Actions Run #570 completed successfully for implementation head `470a4d05a868cf27c6ea9e89736c6df69fd142e4` before merge.

The capability compares two persisted snapshots for the same stock by UUID, preserves caller-selected before/after direction, derives deterministic numeric deltas, exposes classification changes without interpretation, and remains read-only. The API endpoint and dashboard presentation consume the comparison read model without recalculating analytical values.

### Accepted boundary

```
Dashboard
    ↓
HTTP
    ↓
CompareAnalysisSnapshots
    ↓
AnalysisResultStore
    ↓
Persisted Historical Snapshots
```

### Scope boundary

Performance analytics, return calculations, predictive analysis, ranking, charting, portfolio behavior, notifications, and cross-stock comparison remain deferred behind separate design gates.

---

# 23. M23 — Historical Performance Analytics

## Status

M23 is **complete**.

The accepted application capability, API endpoint, and dashboard presentation are implemented. The capability remains read-only and descriptive: it calculates absolute and percentage price change from two persisted snapshots and performs no financial calculation in the frontend.

CI Run #605 passed for the final M23 dashboard commit before merge.

The M23 design gate is **accepted** in `docs/DEC-082-M23-HISTORICAL-PERFORMANCE-ANALYTICS-DESIGN-GATE.md`. Implementation is the next controlled step.

### Accepted boundary

```
Historical Snapshot A
        +
Historical Snapshot B
        ↓
CalculateSnapshotPerformance
        ↓
Descriptive Performance Metrics
        ↓
HTTP / Dashboard consumers
```

M23 calculates absolute price change and percentage price change between two explicitly selected persisted snapshots for the same stock. It uses Decimal arithmetic and preserves caller-selected before/after direction.

Missing prices and a zero baseline produce explicit unavailable metrics rather than fabricated values or division-by-zero behavior.

M23 is descriptive only. It does not evaluate trading strategies, predict future returns, include dividends/costs/benchmarks, manage portfolios, or introduce persistence schema changes.

---

# 24. M24 — Historical Analysis Change Detection

## Status

The M24 design gate is **accepted** in `docs/DEC-083-M24-HISTORICAL-ANALYSIS-CHANGE-DETECTION-DESIGN-GATE.md`. Implementation is the next controlled step.

### Accepted boundary

```
Persisted Snapshot A
        +
Persisted Snapshot B
        ↓
CompareAnalysisSnapshots
        ↓
DetectAnalysisChanges
        ↓
Immutable Change Set
        ↓
API / Dashboard / Future Alert Consumers
```

M24 detects descriptive changes in opportunity classification, technical/fundamental/stock-quality/entry-quality scores, current price, nearest support, and nearest resistance. Optional price availability transitions are changes; both-missing values are unchanged.

The capability reuses M22 comparison semantics, introduces no persistence, no significance thresholds, no notification delivery, and no predictive interpretation.

---

# M25 — Alert Delivery & Notification Boundary

M25 is complete. See `docs/M25-ALERT-DELIVERY-MVP-COMPLETION.md` for the completion record. The accepted design is `docs/DEC-084-M25-ALERT-DELIVERY-DESIGN-GATE.md`.

The implementation provides `DeliverAlert`, a provider-neutral `NotificationProvider`, independent durable delivery state, snapshot-based alert identity, synchronous idempotent delivery, and explicit terminal failure semantics. No external notification provider or API/dashboard delivery integration was introduced.

The latest implementation CI validation observed before merge is GitHub Actions Run #668 on `d8a2759bde75b8530acfaa78af4d2939c4dca426`, which completed successfully.

Deferred: external provider adapters, explicit failed-delivery retry operation, queues/distributed delivery, user notification preferences, delivery analytics, and transport/UI integration.

---

# 25. M24 — Historical Analysis Change Detection

## Status

M24 is **complete**. The accepted design is documented in `docs/DEC-083-M24-HISTORICAL-ANALYSIS-CHANGE-DETECTION-DESIGN-GATE.md`, and the implementation was merged through PR #37.

GitHub Actions Run #626 completed successfully for implementation head `bbb56c089d2582b6aeb8c131067d55c92708e652`, validating the Python unit tests and frontend tests/build workflow.

### Accepted boundary

```
Persisted Snapshot A
        +
Persisted Snapshot B
        ↓
CompareAnalysisSnapshots
        ↓
DetectAnalysisChanges
        ↓
Immutable Change Set
```

The capability detects descriptive changes in classification, technical/fundamental/stock-quality/entry-quality scores, current price, nearest support, and nearest resistance. Optional-value availability transitions are detected explicitly.

M24 reuses M22 snapshot validation, persists no derived change state, introduces no significance thresholds, and performs no notification delivery or predictive interpretation.

Completion record: `docs/M24-HISTORICAL-ANALYSIS-CHANGE-DETECTION-MVP-COMPLETION.md`.

Deferred capabilities remain subject to separate design gates.

---

# 26. M26 — External Notification Provider Integration

## Status

M26 is **complete**. The accepted design is documented in `docs/DEC-085-M26-EXTERNAL-NOTIFICATION-PROVIDER-DESIGN-GATE.md`, and the implementation was merged through PR #41.

Telegram Bot API is integrated behind the existing M25 `NotificationProvider` boundary. Configuration is infrastructure-only, the synchronous request timeout is 10 seconds, no automatic provider retry was added, and deterministic provider tests use an HTTP fake transport.

Completion record: `docs/M26-EXTERNAL-NOTIFICATION-PROVIDER-MVP-COMPLETION.md`.

The implementation does not expose provider credentials, change analytical behavior, or make analysis success depend on notification availability.

Deferred from M26: delivery trigger/API, automatic delivery after analysis, multiple providers, user preferences, notification analytics, queues/workers, distributed delivery, scheduling policy, alert-generation changes, trading execution, and AI notification decisions.

---

# 27. M27 — Alert Delivery Trigger & Transport Boundary

## Status

The M27 design gate is **accepted** in `docs/DEC-086-M27-ALERT-DELIVERY-TRIGGER-DESIGN-GATE.md`. Implementation is authorized for the defined MVP.

The next capability will define an explicit application/API command for delivering an existing alert candidate through M25 `DeliverAlert` and the M26 provider boundary.

The gate preserves these constraints:

- delivery is an explicit side effect, not a GET operation;
- delivery never triggers fresh analysis;
- delivery never recalculates alert eligibility or analytical scores;
- M25 idempotency and durable delivery state remain authoritative;
- provider-specific concepts remain outside application/API contracts;
- M27 MVP is single-alert, synchronous, and sequential.

The accepted command is `POST /api/v1/alerts/{symbol}/deliver?channel=telegram`. It resolves the existing alert candidate, delegates to `DeliverAlert`, preserves M25 idempotency, and does not execute fresh analysis.

---

# 27. M27 — Alert Delivery Trigger & Transport Boundary

## Status

M27 is **complete**. The accepted design is documented in `docs/DEC-086-M27-ALERT-DELIVERY-TRIGGER-DESIGN-GATE.md`, and the implementation was merged through PR #43.

### Accepted boundary

```
POST /api/v1/alerts/{symbol}/deliver
          ↓
DeliverAlertBySymbol
          ↓
GetAlertCandidate + DeliverAlert
          ↓
NotificationProvider
          ↓
TelegramNotificationProvider
```

The command resolves an existing alert candidate, delegates delivery to M25, preserves idempotency and durable delivery state, and never executes fresh analysis.

Transport semantics are explicit: missing candidate → 404; delivery not configured → 503; delivered or persisted failed delivery → 200 with the delivery state.

GitHub Actions Run #730 completed successfully for implementation head `396383e9cd3857459f0f6249f688d279c8cca264`, validating Python unit tests plus frontend tests and build.

Completion record: `docs/M27-ALERT-DELIVERY-TRIGGER-MVP-COMPLETION.md`.

Deferred: automatic delivery after analysis, bulk delivery, multi-channel fan-out, failed-delivery retry, queues/workers, scheduled delivery, user preferences, delivery analytics, trading execution, and AI notification decisions.

---

# 28. M28 — Automatic Alert Delivery Policy

## Status

The M28 design gate is **accepted** in `docs/DEC-087-M28-AUTOMATIC-ALERT-DELIVERY-POLICY-DESIGN-GATE.md`. Implementation is authorized for the defined MVP.

M28 consumes the successful symbols from a completed market-analysis `Execution`, resolves existing candidates through `GetAlertCandidate`, and delegates delivery through `DeliverAlert`. Delivery uses one configured default channel (`telegram`), processes symbols deterministically, isolates per-candidate failures, adds no retry layer, and relies on M25 snapshot/channel idempotency.

M28 is an explicit post-analysis application capability. It is not an implicit side effect of stock analysis, market execution, or scheduling, and it introduces no aggregate delivery persistence.

---

# 28. M28 — Automatic Alert Delivery Policy

## Status

M28 is **complete**. The accepted design is documented in `docs/DEC-087-M28-AUTOMATIC-ALERT-DELIVERY-POLICY-DESIGN-GATE.md`, and the implementation was merged through PR #46.

See `docs/M28-AUTOMATIC-ALERT-DELIVERY-POLICY-MVP-COMPLETION.md` for the completion record.

The automatic-delivery capability consumes successful symbols from a completed market-analysis `Execution`, resolves existing alert candidates, and delegates delivery through M25 `DeliverAlert`. It uses one configured default channel, deterministic ordering, per-candidate failure isolation, and M25 idempotency without adding automatic retry or analytical coupling.

The next capability requires a separate design gate.

---

# 29. M29 — Scheduled Automatic Alert Delivery

## Status

M29 is **complete**. The accepted design is documented in `docs/DEC-088-M29-SCHEDULED-AUTOMATIC-ALERT-DELIVERY-DESIGN-GATE.md`, and the implementation was merged through the scheduled automatic-delivery workflow PR.

Completion record: `docs/M29-SCHEDULED-AUTOMATIC-ALERT-DELIVERY-MVP-COMPLETION.md`.

The implementation head `11a4fbbb4c71e9bf69509bf034b046c48277fba9` passed GitHub Actions Run #823 before merge. The merge commit is `6ca0f2f653aa13cd37e96d0b3b13aa3c9828566e`.

### Accepted boundary

```
Recurring Scheduler
        ↓
RunConfiguredMarketAnalysisWithAutomaticAlertDelivery
        ↓
RunConfiguredMarketAnalysis
        ↓
RunMarketAnalysis
        ↓
RunStockAnalysis

RunConfiguredMarketAnalysisWithAutomaticAlertDelivery
        ↓
AutomaticAlertDelivery
        ↓
DeliverAlert
        ↓
NotificationProvider
```

The workflow invokes automatic delivery for `COMPLETED` and `COMPLETED_WITH_ERRORS` analysis executions and skips delivery for `FAILED` executions. Analysis and delivery outcomes remain independent.

Manual configured-market analysis remains analysis-only.

Deferred: independent delivery schedules, asynchronous delivery, queues/workers, provider retry, multiple channels, user-specific schedules, durable workflow state, and distributed coordination.

### Accepted boundary

```
Recurring Scheduler
        ↓
Scheduled Analysis + Delivery Workflow
        ↓
RunConfiguredMarketAnalysis
        ↓
Analysis Execution
        ↓
AutomaticAlertDelivery
        ↓
DeliverAlert
        ↓
NotificationProvider
```

The workflow composes existing analysis and delivery capabilities. The scheduler remains responsible for timing and recurrence only. Analysis and delivery retain independent outcomes.

M29 will invoke automatic delivery after a returned market-analysis Execution, including partial or failed aggregate executions that contain successful stock symbols. An analysis exception before an Execution exists prevents delivery.

Manual market analysis remains analysis-only.

Deferred: independent delivery schedules, asynchronous delivery, queues/workers, provider retry, multiple channels, user-specific schedules, durable workflow state, and distributed coordination.

---

# 30. M30 — Durable Scheduled Workflow

## Status

The M30 design gate is **accepted** in `docs/DEC-089-M30-DURABLE-SCHEDULED-WORKFLOW-DESIGN-GATE.md`. The durable lifecycle implementation was merged through PR #52, and the recurring-scheduler integration was merged through PR #53. GitHub Actions Run #860 completed successfully for integration head `4115ebd793ae849f9c1b3e1cc8dc4b5537a4676e`.

M30 will persist the lifecycle of one scheduled M29 workflow occurrence independently from analytical-result persistence and alert-delivery persistence.

The MVP states are `CREATED`, `RUNNING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`, and `INTERRUPTED`. Duplicate occurrence starts are idempotent, and persisted RUNNING executions are recoverable as INTERRUPTED after restart. Interrupted executions are detected, not automatically replayed.

The implementation uses SQLite behind a dedicated `ScheduledWorkflowExecutionStore` boundary. Recurring scheduler occurrences now receive deterministic occurrence IDs and are persisted through the durable workflow lifecycle. Restart recovery marks persisted RUNNING executions as INTERRUPTED; interrupted executions are not automatically replayed. Distributed locks, queues, workers, automatic resume, provider retry, multiple channels, and user-specific schedules remain deferred.

---

# 31. M31 — Durable Workflow Recovery

## Status

M31 is **complete**. The accepted design is documented in docs/DEC-090-M31-DURABLE-WORKFLOW-RECOVERY-DESIGN-GATE.md, and the implementation was merged through PR #56.

GitHub Actions Run #899 completed successfully for implementation head `3a4fbc96f00dbc57ec5a929c8f2437df42ffc80d`, validating the M31 unit and integration test changes before merge.

M31 introduces an explicit application recovery command for one persisted INTERRUPTED workflow execution. Recovery reuses the existing workflow execution identity and M29 workflow, relies on existing analysis and alert-delivery idempotency, and does not automatically replay on startup.

The MVP remains sequential and process-local. Step-level checkpoints, automatic resume, distributed coordination, queues, new provider retry policies, and an HTTP recovery endpoint remain deferred.

Completion record: `docs/M31-DURABLE-WORKFLOW-RECOVERY-MVP-COMPLETION.md`.

---

# 32. M32 — Automatic Scheduled Workflow Resume

## Status

M32 is **complete**. The accepted design is documented in `docs/DEC-091-M32-AUTOMATIC-WORKFLOW-RESUME-DESIGN-GATE.md`, and the implementation was merged through PR #58.

Startup now discovers persisted `INTERRUPTED` scheduled workflow executions and delegates recovery to the existing M31 capability. Recovery is deterministic, sequential, process-local, and failure-isolated. Durable-store inspection failure prevents application startup, while an individual recovery failure does not block later attempts.

GitHub Actions Run #937 completed successfully for implementation head `273d34f29af17341ce507b0e04c03e501c0fa138`, validating Python unit tests, frontend tests, and the frontend production build.

See `docs/M32-AUTOMATIC-WORKFLOW-RESUME-MVP-COMPLETION.md`.

---

# 33. M33 — Scheduled Workflow Operational Visibility

## Status

M33 is **complete**. The accepted design is documented in `docs/DEC-092-M33-SCHEDULED-WORKFLOW-OPERATIONAL-VISIBILITY-DESIGN-GATE.md`, and the implementation was merged through PR #60.

GitHub Actions Run #963 completed successfully for implementation head `fd519751b69909ac8203cb3f39fd7ccc9dafc5da`, validating Python unit tests, frontend tests, and the frontend production build.

The application boundary is:

```
ScheduledWorkflowExecutionStore
          ↓
GetScheduledWorkflowExecutions
          ↓
ScheduledWorkflowExecutionReadModel
```

The MVP exposes all persisted scheduled workflow executions, uses deterministic newest-first ordering, supports exact occurrence filtering, and preserves persisted lifecycle/outcome fields without mutating workflow state.

HTTP/dashboard exposure, real-time streaming, pagination/retention, authentication, metrics/tracing, workflow replay, and distributed execution remain deferred.

---

# 33.5. M34 — Scheduled Workflow Operational Visibility API

## Status

M34 is **complete**. The accepted design is documented in `docs/DEC-093-M34-SCHEDULED-WORKFLOW-OPERATIONAL-VISIBILITY-API-DESIGN-GATE.md`, and the implementation was merged through PR #62.

GitHub Actions Run #985 completed successfully for implementation head `3763d86c6577207199ef64fe86072fc179bca8ff`, validating Python unit tests, frontend tests, and the frontend production build.

The HTTP boundary is:

```
GET /api/v1/workflows/executions
        ↓
GetScheduledWorkflowExecutions
        ↓
ScheduledWorkflowExecutionStore
```

The endpoint is read-only, supports exact occurrence filtering, returns a stable `items` envelope, and preserves the persisted workflow execution read model. Workflow execution/recovery semantics remain outside the transport layer.

Deferred: workflow mutation/replay, dashboard presentation, real-time streaming, pagination/retention, authentication, metrics/tracing, scheduler control, notification changes, and distributed execution.

---

# 33.6. M35 — Scheduled Workflow Operational Dashboard

## Status

M35 is **complete**. The accepted design is documented in `docs/DEC-094-M35-WORKFLOW-OPERATIONAL-DASHBOARD-DESIGN-GATE.md`, and the implementation was merged through PR #64.

GitHub Actions Run #1003 completed successfully for implementation head `3ba0ec660470f2a5ee47b886c4df36aed0185033`, validating Python unit tests, frontend tests, and the frontend production build.

The dashboard now presents scheduled workflow executions through the M34 API as a read-only operational panel with explicit loading, empty, unavailable, and error states. Occurrence filtering is explicit and API ordering is preserved.

Workflow control, recovery actions, automatic polling, real-time streaming, pagination, authentication, metrics/tracing, and notification controls remain deferred.

---

# 33.7. M36 — Scheduled Workflow Recovery Control

## Status

The M36 design gate is **accepted** in `docs/DEC-095-M36-SCHEDULED-WORKFLOW-RECOVERY-CONTROL-DESIGN-GATE.md`. The implementation was merged through PR #67. GitHub Actions Run #1043 completed successfully for implementation head `06b671937a9730ead07793cc6cd9acd4c62dc2a9`, validating Python unit tests plus frontend tests and production build.

### Accepted boundary

```
React Dashboard
      ↓
POST /api/v1/workflows/executions/{execution_id}/recover
      ↓
RecoverScheduledWorkflowExecution
      ↓
RecoverDurableScheduledWorkflow
      ↓
RunDurableScheduledWorkflow.recover
      ↓
ScheduledWorkflowExecutionStore
```

The command is synchronous and explicit. Only `INTERRUPTED` executions are recoverable. Missing execution maps to 404; an existing non-recoverable execution maps to 409; successful recovery returns the resulting persisted workflow model. The dashboard exposes an inline Recover action only for interrupted rows, disables only the clicked row while pending, and updates the row from the command response.

M36 does not add authentication, replacement occurrences, new persistence schema, retry policy, polling, bulk recovery, concurrency, or new workflow semantics.

Completion record: `docs/M36-SCHEDULED-WORKFLOW-RECOVERY-CONTROL-MVP-COMPLETION.md`.

---

# 33.8. M38 — Multi-User Identity & Ownership

## Status

The M38 design gate is **accepted** in `docs/DEC-097-M38-MULTI-USER-IDENTITY-DESIGN-GATE.md`. The first implementation slice is complete and merged through PR #73. GitHub Actions Run #1221 passed on implementation head `f335c67d`. The slice establishes the immutable user lifecycle model, application identity contract, explicit ownership authorization boundary, and deterministic M37 legacy operator mapping. Persistence/reload and migration of concrete user-owned capabilities remain before M38 can be marked complete.

### Accepted boundary

```
HTTP / Authentication Adapter
          ↓
AuthenticatedIdentity
          ↓
Application Authorization Boundary
          ↓
User-Owned Application Capability
          ↓
Domain / Persistence
```

M38 uses a hybrid identity boundary with immutable internal user UUIDs. Authentication remains adapter-owned and replaceable. User-owned resources carry explicit ownership references; system/global resources remain explicitly global. M37 operator authentication remains temporarily available only as a compatibility path.

The MVP defines ACTIVE, DISABLED, and DELETED user lifecycle states and explicit 401/403/404 semantics for protected resources.

Deferred: commercial identity-provider selection, social login, MFA, SSO, organizations/teams, role-management UI, billing, trading authorization, audit-log product design, rate limiting/WAF, notification preferences, and AI authorization policy.

---

## M39 — Multi-User Authentication & Identity Transport

### Status

M39 is **complete** for the accepted MVP scope. The design gate is documented in `docs/DEC-099-M39-MULTI-USER-AUTHENTICATION-DESIGN-GATE.md`, and the implementation was merged through PR #81.

GitHub Actions Run #1346 completed successfully for the M39 implementation head, validating Python unit tests, frontend tests, and the frontend production build.

Completion record: `docs/M39-MULTI-USER-AUTHENTICATION-MVP-COMPLETION.md`.

### Accepted first slice

- configured per-user bearer credentials;
- immutable internal user UUID resolution;
- lifecycle validation on every protected request;
- scheduled workflow execution read/recovery as the first user-owned API/application surface;
- existing application ownership authorization remains authoritative;
- M37 operator authentication remains as an explicit compatibility path;
- frontend login/session UX remains deferred.

The first concrete authentication mechanism is intentionally controlled-deployment infrastructure rather than a complete identity-management product. A future external identity provider can replace the adapter without changing ownership semantics.

### Deferred

- external identity-provider integration;
- local username/password accounts;
- MFA/SSO;
- organizations/teams;
- delegated access;
- user-management UI;
- distributed session storage;
- automatic retirement of M37 operator compatibility.

## M40 — Frontend Authentication & User Credential Lifecycle## M41 — User Management & Credential Administration

### Status

The M41 design gate is **accepted** in `docs/DEC-102-M41-USER-MANAGEMENT-DESIGN-GATE.md`. Implementation is the next controlled step.

M41 adopts self-service credential administration plus operator-controlled user lifecycle administration. Operators create, disable, reactivate, delete, and administer users and credentials. Users may rotate their own credential atomically with replacement.

Deletion is a `DELETED` lifecycle transition; historical ownership remains attributable and is never silently reassigned. User profile data beyond UUID and lifecycle state is deferred.

A minimal durable management-audit boundary is required for security-sensitive lifecycle and credential commands, without storing raw credentials.

The first user-management implementation must preserve the existing authentication → authenticated identity → application authorization boundary and keep analytical domain modules identity-agnostic.

Deferred: registration, passwords, MFA/SSO, external identity providers, profile fields, delegated access, organizations, richer roles, audit query UI, and automatic credential expiration.

---



### Status

M40 is **complete** for the accepted DEC-100 and DEC-101 MVP scope.

The frontend authentication/session slice was merged through PR #84. The durable credential lifecycle implementation was merged through PR #88.

GitHub Actions Run #1420 completed successfully for the M40 credential-lifecycle implementation head, validating Python unit tests, frontend tests, and the frontend production build.

The system now supports durable opaque bearer credentials behind a dedicated CredentialStore, one-time credential provisioning/rotation results, revocation, disabled/deleted user rejection, and M39 configured-credential compatibility. The existing frontend session UX remains the transport boundary.

Deferred: passwords, password recovery, MFA/SSO, external identity providers, automatic credential expiration, self-service registration, user-management UI, organizations/teams, delegated access, and distributed session storage.

Completion record: `docs/M40-USER-AUTHENTICATION-CREDENTIAL-LIFECYCLE-MVP-COMPLETION.md`.

---

# 33.9. M42 — Management Audit Reporting

## Status

M42 is **complete**. The accepted design is documented in `docs/DEC-103-M42-MANAGEMENT-AUDIT-REPORTING-DESIGN-GATE.md`, and the implementation was merged through PR #93.

GitHub Actions Run #1544 completed successfully for the implementation head, validating Python unit tests, frontend tests, and the frontend production build.

Completion record: `docs/M42-MANAGEMENT-AUDIT-REPORTING-MVP-COMPLETION.md`.

### Accepted boundary

```
React Dashboard
      ↓
HTTP API
      ↓
GetManagementAudit
      ↓
ManagementAuditStore
      ↓
SQLite
```

The MVP is operator-only and read-only. It exposes actor/target UUIDs, action, outcome, and stored UTC timestamp; supports actor, target, action, outcome, and time-range filters; orders deterministically by `occurred_at DESC, audit_id DESC`; and uses bounded pagination with a default page size of 50 and maximum of 100.

Retention remains unchanged. No audit-write behavior, credentials, lifecycle semantics, new permission model, real-time streaming, SIEM integration, analytics, or user self-service audit history is introduced.

# 33.10. M43 — User-Facing Audit History

## Status

M43 is **complete**. The accepted design is documented in `docs/DEC-104-M43-USER-FACING-AUDIT-HISTORY-DESIGN-GATE.md`, and the implementation was merged through PR #96.

GitHub Actions Run #1599 completed successfully for the implementation head, validating Python unit tests, frontend tests, and the frontend production build.

Completion record: `docs/M43-USER-FACING-AUDIT-HISTORY-MVP-COMPLETION.md`.

### Accepted boundary

```
AuthenticatedIdentity
        ↓
GetUserAuditHistory
        ↓
ManagementAuditStore
        ↓
SQLite
```

The MVP uses target-only visibility, safe action/outcome/time filters, M42 bounded pagination and deterministic ordering, and a dedicated authenticated endpoint at `GET /api/v1/users/me/audit`.

The user-facing read model redacts raw actor/target UUIDs and exposes only relative actor labels (self/operator) and self-scoped event data. Unknown audit actions are excluded by default.

M41 audit writes, M42 operator reporting, lifecycle semantics, credentials, and analytical modules remain unchanged.

Deferred: richer audit permissions, actor-or-target history, organizations/delegated access, retention policy, real-time streaming, audit analytics, SIEM integration, and cross-user audit visibility.

---

# 33. Cross-Cutting Requirements

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

# 33.11. M45 — Scheduled Workflow Lifecycle History Visibility

## Status

M45 is **complete**. The accepted design is documented in `docs/DEC-106-M45-SCHEDULED-WORKFLOW-LIFECYCLE-HISTORY-VISIBILITY-DESIGN-GATE.md`, and the implementation was merged through PR #104.

The implementation head `292d12bacb6a84cf8a102c6b816bd2bac8a7b0fc` passed GitHub Actions Run #1738 with:

- Python unit tests: **success**
- Frontend tests: **success**
- Frontend production build: **success**

Completion record: `docs/M45-SCHEDULED-WORKFLOW-LIFECYCLE-HISTORY-VISIBILITY-MVP-COMPLETION.md`.

### Accepted boundary

```
HTTP / Dashboard
       ↓
GetScheduledWorkflowExecutionHistory
       ↓
ScheduledWorkflowExecutionStore
       ↓
SQLite lifecycle history
```

The MVP exposes one execution's persisted lifecycle history through a dedicated immutable read model, preserves authoritative ascending sequence order, exposes persisted transition reasons, represents the initial transition with `from_state = null`, and reuses the existing owner-or-global authorization boundary.

The API endpoint and dashboard are read-only presentation surfaces. No lifecycle mutation, replay, analytics, pagination, schema change, or new authentication model was introduced.

---

# 34. Milestone Completion Rule

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

# 35. Changing the Roadmap

The roadmap may change when requirements change, an architectural assumption proves incorrect, new evidence becomes available, a dependency becomes unavailable, or a milestone reveals a better sequence.

Changes affecting architecture or important domain decisions must be recorded in `docs/DECISION_LOG.md` or a dedicated DEC document.

The current execution-order change is recorded in `docs/DEC-047-EXECUTION-SEQUENCE-UPDATE.md`.

---

# 36. Guiding Principle

> **Build the analytical brain first. Add the reliability, acquisition, automation, and interface layers around a core whose behavior is already understood.**

# 32. M32 — Automatic Scheduled Workflow Resume

### M32 — Automatic Scheduled Workflow Resume

M32 is **complete**. The accepted design is documented in `docs/DEC-091-M32-AUTOMATIC-WORKFLOW-RESUME-DESIGN-GATE.md`, and the implementation was merged through PR #58.

Startup now discovers persisted `INTERRUPTED` scheduled workflow executions and delegates recovery to the existing M31 capability. Recovery is deterministic, sequential, process-local, and failure-isolated. Durable-store inspection failure prevents application startup, while an individual recovery failure does not block later attempts.

GitHub Actions Run #937 completed successfully for implementation head `273d34f29af17341ce507b0e04c03e501c0fa138`, validating Python unit tests, frontend tests, and the frontend production build.

See `docs/M32-AUTOMATIC-WORKFLOW-RESUME-MVP-COMPLETION.md`.

---

