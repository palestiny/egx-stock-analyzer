# M20 — Historical Analysis Result History MVP Completion

**Status:** Complete  
**Date:** 2026-09-18  
**Design Gate:** `docs/DEC-079-M20-HISTORICAL-ANALYSIS-RESULT-HISTORY-DESIGN-GATE.md`  
**Implementation PR:** #24

## Delivered

M20 adds immutable historical analysis-result snapshots behind the existing `AnalysisResultStore` boundary.

### Application boundary

```
Analysis / Scheduled Execution
          ↓
AnalysisResultStore
          ↓
Historical Analysis Result Repository
          ↓
SQLite
```

### Behavior

- each persisted snapshot has a UUID identity;
- multiple completed snapshots for the same symbol are supported;
- multiple snapshots on the same analysis date are supported;
- `get(symbol)` and `get_record(symbol)` retain latest-result compatibility;
- latest is derived from persisted history;
- history retrieval supports optional inclusive date bounds;
- history ordering is deterministic: analysis date descending, snapshot UUID ascending;
- failed analysis does not create a successful historical snapshot;
- historical reads never execute fresh analysis;
- corrupt or unsupported serialized payloads remain explicit persistence errors.

## SQLite Migration

The previous latest-only `analysis_results` schema is migrated in place to the history-capable representation. Existing stored rows are preserved as one historical snapshot each.

No synthetic history is created for periods that were not previously stored.

## Compatibility

The current report and alert application capabilities continue to consume `get(symbol)`; no HTTP or dashboard history surface was added in M20.

SQLite inspection continues to display the latest snapshot per symbol.

## Validation

GitHub Actions Run #430 completed successfully for implementation head `1a8f72eaeeec57306e9dcdc1f4de113863f13eac`.

Validated jobs:

- Python unit tests: **success**
- Frontend tests and production build: **success**

## Deferred

- historical HTTP/dashboard endpoints;
- historical ranking;
- change detection;
- performance analytics;
- historical market-data warehousing;
- watchlists;
- notifications;
- portfolio/trading behavior;
- AI analysis.

These require separate design gates.
