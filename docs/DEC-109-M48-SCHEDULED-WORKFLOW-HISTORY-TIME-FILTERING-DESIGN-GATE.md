# DEC-109 — M48 Scheduled Workflow History Time-Range Filtering Design Gate

**Status:** Accepted  
**Date:** 2026-09-20  
**Milestone:** M48

## 1. Problem

M47 added typed lifecycle-state filtering to the single-execution scheduled-workflow history read boundary. Operational consumers can now isolate transition states, but cannot constrain history to a time window without retrieving unrelated transitions.

## 2. Desired Outcome

Allow an authorized caller to request one execution's lifecycle history within an explicit UTC time range while preserving persisted sequence as the sole ordering authority, M45 complete-history compatibility, M46 cursor pagination, M47 state filtering, ownership authorization, and read-only behavior.

## 3. Boundary

```
HTTP / Dashboard
       ↓
GetScheduledWorkflowExecutionHistory
       ↓
ScheduledWorkflowExecutionStore
       ↓
SQLite lifecycle history
```

M48 extends the existing query capability. No second history-query abstraction is introduced.

## 4. Accepted Contract

Optional `occurred_from` and `occurred_to` parameters are accepted as UTC ISO-8601 timestamps.

- `occurred_from` is inclusive.
- `occurred_to` is exclusive.
- Supplying neither preserves existing behavior.
- Supplying only one creates a one-sided bound.
- Supplying both requires `occurred_from < occurred_to`.
- Invalid timestamps and invalid ranges are rejected explicitly.
- A valid range with no matches returns an empty page.
- Existing `from_state` and `to_state` filters compose with the time range using AND semantics.
- Filtering occurs in persistence before pagination.
- Ordering remains ascending by persisted sequence, never by timestamp.
- Continuation cursors are bound to the complete effective query shape, including state and time filters.
- Existing legacy unfiltered cursors remain compatible.
- Ownership authorization remains unchanged.
- Reads remain read-only and scoped to one execution.

## 5. Alternatives

### A. Client-side time filtering
Rejected for the MVP because it transfers unrelated history and duplicates query semantics in consumers.

### B. Timestamp-only ordering
Rejected because persisted sequence is the authoritative lifecycle order and timestamps are not the lifecycle identity.

### C. Add time filtering to the existing query capability
Accepted because it extends the established M45–M47 read boundary without introducing a parallel abstraction.

## 6. Persistence Decision

The existing lifecycle-history source remains authoritative. The current primary key `(execution_id, sequence)` remains sufficient for the MVP query contract. No mandatory secondary index is introduced without measured evidence that the bounded single-execution query requires one.

## 7. Presentation

The API exposes the query parameters directly. The dashboard may provide a simple UTC date/time filter using the same API contract; it must not filter the returned collection locally.

## 8. Explicitly Deferred

- cross-execution history search;
- full-text reason search;
- arbitrary ordering;
- retention/deletion;
- aggregation and analytics;
- event replay;
- new authorization semantics;
- new persistence sources.

## 9. TDD Acceptance Criteria

- omitted time filters preserve M47 behavior;
- inclusive lower bound;
- exclusive upper bound;
- only lower bound;
- only upper bound;
- invalid timestamp;
- invalid range;
- no-match range;
- state + time filter composition;
- sequence ordering remains deterministic;
- first-page filtering;
- continuation pagination over filtered results;
- cursor reuse with different effective time filters is rejected;
- empty history;
- unknown execution;
- owner/global authorization;
- another-user rejection;
- restart consistency;
- filtered reads do not mutate workflow state;
- API passes filters through without reconstructing history.

## 10. Design Gate Decision

**Accepted — M48 implementation is authorized within the scope above.**
