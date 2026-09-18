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

### Report

`GET /api/v1/reports/{symbol}`

Semantics:

- read-only
- returns the latest stored analysis report for the symbol
- does not trigger analysis
- returns 404 when the stock/result is unavailable
- response is a transport DTO
- report contents are derived from the already-computed analysis

The report transport DTO explicitly exposes presentation-safe values only:

- symbol and preserved analysis date
- fundamental period end
- technical/fundamental/stock-quality/entry-quality scores
- opportunity classification
- current price and nearest support/resistance when available
- technical trend/momentum/volume statuses
- fundamental profitability/liquidity/growth statuses

Domain objects, UUID identity, and scoring/evidence objects are not returned directly.

### Alert Candidate

`GET /api/v1/alerts/{symbol}`

Semantics:

- read-only projection of the latest stored analysis
- returns the alert candidate when the stored opportunity classification is BUY
- returns 404 when no alert candidate exists for the latest result
- does not send a notification
- does not persist or deduplicate alerts

The alert transport DTO exposes the stock identity, classification, stock-quality score, and entry-quality score. It does not expose notification-delivery behavior.

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

## 8. Implementation Status

The analysis period prerequisite and read-side projections are now implemented:

- `AnalysisResultRecord` preserves `StockAnalysisResult` plus `analysis_date`.
- `RunStockAnalysis` passes its `as_of` date into the analysis execution.
- `InMemoryAnalysisResultStore` exposes the stored record without breaking the existing `get()` contract.
- `GetAnalysisReport` composes the existing M11 `AnalysisReport` from the stored result and preserved analysis date.
- `GetAlertCandidate` delegates BUY-only alert semantics to the existing M11 `AlertGenerator`.
- `AnalysisReportResponse` and `AlertCandidateResponse` are explicit transport DTOs.
- `GET /api/v1/reports/{symbol}` and `GET /api/v1/alerts/{symbol}` are read-only API projections.
- No notification infrastructure, persistence, deduplication, or scheduling was introduced.

## 9. Validation

Application-level report tests cover unknown stock, missing result, preserved analysis date, and legacy results without an analysis date.

API contract tests cover:

- report endpoint not configured
- missing report
- successful report projection with preserved analysis date
- alert endpoint not configured
- non-BUY alert absence
- successful BUY alert projection

The new tests have been committed to the branch but still require local execution before their pass status is claimed.

## 10. Next Gate

The next M12 design gate should address how these read-side projections are consumed by a dashboard/presentation layer, while keeping dashboard-specific presentation concerns outside the domain and application analysis rules.

No notification infrastructure is introduced by this gate.
