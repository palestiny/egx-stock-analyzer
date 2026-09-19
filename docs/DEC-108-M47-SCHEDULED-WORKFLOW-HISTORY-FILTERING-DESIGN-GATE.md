# DEC-108 — M47 Scheduled Workflow History Filtering Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M47

## 1. Context

M45 established the read-only lifecycle-history projection for one scheduled workflow execution. M46 added bounded sequence-cursor pagination while preserving the M45 complete-history behavior.

M46 intentionally deferred filtering by transition state or transition reason.

If operators need to isolate relevant lifecycle events without loading unrelated transitions, the next design question is whether filtering belongs in the existing history read capability and, if so, what semantics are safe and deterministic.

## 2. Problem

A lifecycle history may contain multiple transition types and reasons. Pagination bounds response size, but it does not let a caller answer focused questions such as:

- show only transitions into FAILED or INTERRUPTED;
- show only transitions with a recorded reason;
- identify recovery-related transitions;
- inspect a subset of lifecycle events without client-side filtering.

Client-side filtering is possible, but it requires retrieving pages that may contain mostly irrelevant events and makes query semantics transport-specific.

## 3. Desired Outcome

If accepted, M47 should define a bounded, read-only filtering extension over the existing M46 history query capability without changing lifecycle persistence or mutation semantics.

The result must preserve:

- one execution as the query scope;
- persisted sequence as the ordering authority;
- existing ownership authorization;
- sequence-cursor pagination;
- complete-history compatibility when filters are omitted;
- no history reconstruction or mutation.

## 4. Proposed Boundary

```
HTTP / Dashboard
       ↓
GetScheduledWorkflowExecutionHistory
       ↓
ScheduledWorkflowExecutionStore
       ↓
SQLite lifecycle history
```

Filtering should extend the existing capability rather than introduce a second history query path.

## 5. In Scope

- transition-state filtering;
- reason-presence filtering if justified;
- interaction between filters and sequence-cursor pagination;
- deterministic ordering;
- explicit validation;
- store query semantics;
- API contract tests;
- dashboard presentation only if accepted.

## 6. Out of Scope

- free-text full-text search;
- cross-execution filtering;
- analytics or aggregation;
- lifecycle mutation;
- event replay/event sourcing;
- retention/deletion;
- new authentication/authorization;
- arbitrary client-controlled ordering.

## 7. Alternatives

### A. Keep filtering client-side

Pros:
- no new backend query semantics;
- simplest persistence boundary.

Cons:
- inefficient for large histories;
- clients must understand lifecycle event semantics;
- repeated pagination may be required to find relevant events.

### B. State-transition filters

Example: filter by to_state, optionally from_state.

Pros:
- directly maps to persisted lifecycle fields;
- deterministic and indexable;
- easy to explain.

Cons:
- does not cover reason-oriented investigations.

### C. Reason filters

Example: exact reason matching or reason-presence.

Pros:
- useful for operational investigations.

Cons:
- reasons are free-form application text and are less stable as a query contract.

### D. Combined structured filters

Allow a small allowlisted set of transition-state predicates and reason-presence.

Pros:
- useful without introducing free-text search;
- keeps semantics tied to stable lifecycle structure.

Cons:
- larger contract and more test cases.

## 8. Open Questions

1. Should M47 allow only to_state filters, or both from_state and to_state?
2. Should reason filtering be exact-match, presence/absence only, or deferred entirely?
3. Should multiple filters use AND semantics?
4. How should filters interact with the existing sequence cursor?
5. Should the cursor encode the active filter fingerprint to prevent unsafe cursor reuse across different queries?
6. Is a dedicated SQLite index justified for the accepted filter shape?
7. Should the dashboard expose filtering immediately or keep M47 API/application-only?
8. What compatibility guarantee is required for existing M45/M46 callers?

## 9. Proposed Invariants

- persisted sequence remains the sole ordering authority;
- one execution remains the query scope;
- filters never mutate lifecycle state;
- authorization remains identical to M45/M46;
- pagination remains deterministic;
- a cursor cannot silently change the effective query;
- omitted filters preserve current behavior;
- store retrieval remains the persistence source of truth.

## 10. TDD Acceptance Shape

If accepted, tests should cover:

- no filters preserves current M46 behavior;
- one accepted state filter;
- multiple filters;
- filter + first page;
- filter + continuation cursor;
- cursor reuse with different filters;
- invalid filter values;
- empty filtered result;
- owner/global authorization;
- another-user rejection;
- stable ordering;
- restart consistency;
- no mutation caused by filtered reads;
- API transport mapping;
- dashboard behavior if dashboard scope is accepted.

## 11. Design Gate Decision

**Status: Proposed — implementation is not authorized.**

M46 remains complete and unchanged while this design is evaluated.

The next action is to resolve the open questions and record an accepted M47 decision before implementation.
