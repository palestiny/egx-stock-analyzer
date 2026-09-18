# M21 — Historical Analysis View MVP Completion

**Status:** Complete  
**Date:** 2026-09-18  
**Design Gate:** `docs/DEC-080-M21-HISTORICAL-ANALYSIS-VIEW-DESIGN-GATE.md`

## Outcome

M21 exposes the immutable historical analysis snapshots introduced by M20 through the existing application, HTTP, and dashboard boundaries.

The feature is read-only: historical views consume persisted snapshots and never recalculate historical analysis.

## Implemented

- `GetAnalysisHistory` application query capability;
- snapshot-aware historical response DTO;
- `GET /api/v1/history/{symbol}`;
- inclusive `from_date` and `to_date` query bounds;
- explicit unknown-symbol versus empty-history semantics;
- API/runtime/composition wiring;
- frontend historical-analysis API client;
- deterministic newest-first historical snapshot list;
- dashboard loading, empty, and history-error states;
- frontend API and dashboard contract coverage;
- preservation of the existing latest report and alert contracts.

## Boundary Preserved

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

The dashboard remains a presentation client. The API remains a transport adapter. Historical query orchestration stays in the application layer, while persistence and ordering remain behind `AnalysisResultStore`.

No historical analytical recalculation, scoring changes, ranking, charting, notifications, watchlists, trading behavior, or persistence-schema changes were introduced.

## Validation

GitHub Actions Run #484 completed successfully for implementation head:

```
4f2d047461b2ffa5e05d3cdc4d22cdee3f0e6eb9
```

The workflow validated:

- Python unit tests: **success**
- Frontend tests: **success**
- Frontend production build: **success**

The implementation was merged through PR #28.

## Deferred

The following remain outside M21:

- historical OHLC charting;
- historical ranking;
- performance/return analytics;
- change-detection rules;
- notifications and change alerts;
- watchlists;
- portfolio/trading behavior;
- authentication/authorization;
- pagination;
- AI analysis.

Any derived historical analytics or expanded presentation behavior requires a separate design gate.

## Completion Rule

M21 satisfies the project milestone sequence:

```
Design
 ↓
Tests
 ↓
Implementation
 ↓
Review / Fix
 ↓
Documentation
 ↓
Git Commit
 ↓
Milestone Complete
```
