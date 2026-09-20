# DEC-080 — M21 Historical Analysis View Design Gate

**Status:** Accepted  
**Date:** 2026-09-18  
**Milestone:** M21 — Historical Analysis View

---

## 1. Problem

M20 now preserves immutable completed analysis snapshots and provides deterministic historical retrieval behind `AnalysisResultStore`.

The current API and dashboard still expose only the latest analysis result.

This creates a deliberate presentation gap: the system can retain historical analytical state, but users cannot inspect that history through the existing user-facing boundary.

M21 defines the smallest read-only application/API/dashboard capability needed to expose stored analysis history without moving analytical or persistence responsibilities into the presentation layer.

---

## 2. Desired Outcome

M21 should allow a client to:

1. request historical analysis snapshots for a stock;
2. receive deterministic newest-first results;
3. optionally constrain the query by date range;
4. distinguish an empty history from a transport/server failure;
5. preserve the existing latest report/alert contracts;
6. render historical snapshots without recalculating analytical values;
7. keep persistence and query mechanics behind application/infrastructure boundaries.

---

## 3. In Scope

- application-level historical analysis query use case;
- transport DTO for historical snapshots;
- read-only HTTP endpoint;
- date-bound query parameters;
- deterministic ordering inherited from M20;
- empty-history semantics;
- dashboard presentation of historical snapshots;
- API/client/component tests;
- explicit compatibility with existing latest-result endpoints.

---

## 4. Out of Scope

- recalculating historical analysis;
- changing scoring or opportunity classification;
- historical ranking;
- performance analytics or return calculations;
- change-detection rules;
- notifications;
- watchlists;
- portfolio/trading behavior;
- historical OHLC charting;
- real-time streaming;
- persistence schema changes;
- authentication/authorization;
- AI analysis.

---

## 5. Proposed Boundary

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

The dashboard remains a presentation client. The API remains a transport adapter. The application use case owns query orchestration and validation. The store owns persistence and ordering mechanics.

---

## 6. API Shape Candidate

A read-only endpoint is proposed:

```
GET /api/v1/history/{symbol}
```

Optional query parameters:

```
from_date=YYYY-MM-DD
to_date=YYYY-MM-DD
```

The exact transport field names and validation rules must be accepted before implementation.

The endpoint must never trigger fresh analysis.

---

## 7. Empty and Error Semantics Candidate

A valid request with no historical snapshots should return HTTP 200 with an empty collection.

Invalid date syntax or an invalid date range should be a client validation error.

An unknown stock symbol should remain distinguishable from a valid symbol with no stored history.

Persistence failures should remain server-side failures and must not be represented as an empty history.

These semantics require acceptance before implementation.

---

## 8. Alternatives

### A. Expose the store directly through FastAPI

**Benefit:** very little application code.

**Trade-off:** transport becomes coupled to persistence contract and leaks infrastructure-oriented query semantics.

### B. Dedicated `GetAnalysisHistory` application use case

**Benefit:** keeps the read-side boundary explicit, testable, and independent of HTTP.

**Trade-off:** adds a small application abstraction.

**Preferred candidate:** B.

### C. Extend the existing report endpoint

**Benefit:** fewer endpoints.

**Trade-off:** mixes latest snapshot presentation with collection/history semantics and makes the existing report contract less stable.

---

## 9. Accepted Decisions

1. **Endpoint:** use `GET /api/v1/history/{symbol}`, consistent with the existing report and alert resource pattern.
2. **Response shape:** return an object containing the normalized symbol and an `items` collection. Each item contains the persisted snapshot UUID, analysis date, and the same analytical result fields already represented by the existing report/read-side transport mapping. No new analytical calculations are introduced.
3. **Date bounds:** `from_date` and `to_date` are inclusive, matching the business interpretation of a requested analysis-date range.
4. **Invalid range:** `from_date > to_date` is a client validation error.
5. **Unknown symbol:** an unknown catalog symbol returns 404. A known symbol with no stored history returns 200 with an empty `items` collection.
6. **Dashboard presentation:** the first MVP renders a deterministic table/list of historical snapshots. Charting is deferred.
7. **Unbounded result size:** the MVP returns all matching snapshots. Pagination is deferred until actual history volume demonstrates the need.
8. **Read-only behavior:** the endpoint never triggers fresh analysis. Persistence failures remain server errors rather than empty-history responses.

### Response Contract

Conceptually:

```json
{
  "symbol": "EGAL",
  "items": [
    {
      "snapshot_id": "...",
      "analysis_date": "2026-09-18",
      "...": "existing analytical result fields"
    }
  ]
}
```

The historical item is a presentation of an already-persisted snapshot. It is not a new analytical model.

---

## 10. Open Questions

1. Should the endpoint be `/history/{symbol}` or nested under `/analysis/{symbol}/history`?
2. What exact response shape should represent each historical snapshot?
3. Should date bounds be inclusive?
4. What should happen when `from_date > to_date`?
5. Should an unknown symbol return 404 even when its history is empty?
6. Should the dashboard initially show a table/list or a chart?
7. How many snapshots should the MVP return when no limit is supplied?
8. Should pagination be deferred until evidence requires it?

The design questions are resolved by the accepted decisions above. Implementation is authorized for the defined M21 MVP.

---

## 10. Initial TDD Acceptance Shape

The accepted implementation should test:

- history query for a symbol with multiple snapshots;
- deterministic newest-first ordering;
- inclusive date bounds;
- empty valid history;
- invalid date range;
- unknown symbol;
- persistence/query failure mapping;
- no fresh analysis execution;
- API response contract;
- frontend rendering of historical rows;
- frontend empty/loading/error states;
- existing latest report/alert endpoints remain unchanged.

---

## 12. Design Gate Decision

**Status: Accepted — implementation is authorized for the M21 MVP defined here.**

---

## 13. Revisit Conditions

Revisit this gate if the requirement changes from simple historical inspection to analytics, charting, ranking, comparison, performance measurement, or other derived historical behavior. Those capabilities should receive separate design gates rather than expanding M21 opportunistically.
