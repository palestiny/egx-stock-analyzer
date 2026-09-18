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

# 24. Cross-Cutting Requirements

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

# 25. Milestone Completion Rule

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

# 26. Changing the Roadmap

The roadmap may change when requirements change, an architectural assumption proves incorrect, new evidence becomes available, a dependency becomes unavailable, or a milestone reveals a better sequence.

Changes affecting architecture or important domain decisions must be recorded in `docs/DECISION_LOG.md` or a dedicated DEC document.

The current execution-order change is recorded in `docs/DEC-047-EXECUTION-SEQUENCE-UPDATE.md`.

---

# 27. Guiding Principle

> **Build the analytical brain first. Add the reliability, acquisition, automation, and interface layers around a core whose behavior is already understood.**
