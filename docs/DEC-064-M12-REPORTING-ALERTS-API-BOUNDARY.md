# DEC-064 — M12 Reporting & Alerts API Boundary

**Status:** Accepted

## 1. Design Question

How should M12 expose the existing M11 reporting and alert capabilities without moving reporting, opportunity rules, or notification behavior into FastAPI?

## 2. Existing M11 Capabilities

M11 already provides:

- immutable `AnalysisReport` composition from supplied analytical results
- immutable `AlertCandidate` generation for BUY classifications
- no recalculation in reporting
- no notification delivery in alert generation

These remain the source of truth for report/alert semantics.

## 3. Decision

M12 will expose reporting and alerting only as **read-side projections of an already completed analysis**.

The API layer may:

- locate the requested stock through the application stock catalog
- retrieve the latest stored analysis result
- compose a transport DTO from the existing report/alert capability
- map application conditions to HTTP responses

The API layer must not:

- calculate scores
- classify opportunities
- decide BUY thresholds
- generate notifications
- persist alerts
- schedule delivery
- implement deduplication
- own provider behavior

## 4. Important Current Boundary

The current `AnalysisResultStore` stores only `StockAnalysisResult`. It does not currently store analysis-period metadata alongside the result.

M11 `AnalysisReport` explicitly contains `analysis_date`.

Therefore M12 must **not invent or imply historical/freshness semantics** for a report endpoint by using `date.today()` as if it were the actual analysis date.

Before committing a report HTTP endpoint, the application result representation must provide the actual analysis period/date associated with the stored result.

This is a deliberate prerequisite, not an implementation detail to hide inside FastAPI.

## 5. Proposed Read Surface

Once the application result representation carries the analysis period:

### Report

`GET /api/v1/reports/{symbol}`

Semantics:

- read-only
- returns the latest stored analysis report for the symbol
- does not trigger analysis
- returns 404 when the stock/result is unavailable
- response is a transport DTO
- report contents are derived from the already-computed analysis

### Alert Candidate

`GET /api/v1/alerts/{symbol}`

Semantics:

- read-only projection of the latest stored analysis
- returns the alert candidate when the stored opportunity classification is BUY
- returns 404 when no alert candidate exists for the latest result
- does not send a notification
- does not persist or deduplicate alerts

A separate notification-delivery endpoint is explicitly out of scope.

## 6. Why This Boundary

The API should expose application capabilities, not recreate domain behavior.

Keeping report/alert composition below FastAPI preserves:

```
Stored Analysis
      ↓
Application capability
      ↓
M11 Report / Alert semantics
      ↓
API transport DTO
      ↓
HTTP
```

rather than:

```
HTTP
  ↓
FastAPI
  ↓
business rules
  ↓
notification logic
```

## 7. Deferred

The following remain outside this gate:

- report persistence/history
- alert persistence/history
- alert deduplication/state transitions
- alert severity/throttling
- notification channels
- scheduling
- watchlists
- ranking/top opportunities
- dashboard-specific business logic
- authentication/authorization
- production observability

## 8. Prerequisite Implementation Status

The analysis period prerequisite is now implemented in the application layer:

- `AnalysisResultRecord` preserves `StockAnalysisResult` plus `analysis_date`.
- `RunStockAnalysis` passes its `as_of` date into the analysis execution.
- `InMemoryAnalysisResultStore` exposes the stored record without breaking the existing `get()` contract.
- `GetAnalysisReport` composes the existing M11 `AnalysisReport` from the stored result and preserved analysis date.
- Report composition returns no report when the result has no preserved analysis date, avoiding invented freshness semantics.

Contract tests were added for unknown stock, missing result, preserved analysis date, and legacy results without an analysis date.

## 9. Next Implementation Gate

Before adding the HTTP report endpoint, define the report transport DTO explicitly. The DTO must expose presentation-safe fields without leaking domain objects or moving report semantics into FastAPI.

Acceptance criteria for that prerequisite:

1. The actual analysis date/period survives from the analysis command to the stored result.
2. Existing analysis GET/POST behavior remains compatible.
3. Report composition uses the stored analysis period, not the current wall-clock date.
4. Alert projection uses the stored analysis result without recalculating classification.
5. API contract tests cover missing result, successful report projection, BUY alert projection, and non-BUY alert absence.

No notification infrastructure is introduced by this gate.
