# DEC-108 — M47 Scheduled Workflow History Filtering Design Gate

**Status:** Accepted  
**Date:** 2026-09-20  
**Milestone:** M47

## 1. Problem

M46 completed bounded sequence-cursor pagination for one scheduled workflow execution's lifecycle history. The history read boundary is now bounded, but callers still receive every persisted transition in the selected execution.

Operational consumers may need to inspect only transitions relevant to a state or lifecycle direction without downloading unrelated history and filtering it in the client.

M47 should decide whether and how a narrow, server-side lifecycle-history filtering capability is justified.

## 2. Desired Outcome

An authorized caller should be able to request a bounded lifecycle-history view for one execution with explicit, deterministic filters while preserving persisted sequence as the sole ordering authority, existing M45 complete-history compatibility, M46 cursor pagination semantics, ownership authorization, read-only behavior, and the existing SQLite history source of truth.

Filtering must reduce the returned read model only. It must never mutate, reconstruct, or reinterpret lifecycle history.

## 3. Proposed Boundary

```
HTTP / Dashboard
       ↓
GetScheduledWorkflowExecutionHistory
       ↓
ScheduledWorkflowExecutionStore
       ↓
SQLite lifecycle history
```

M47 should extend the existing read-side capability rather than introduce a second history-query abstraction.

## 4. In Scope

- explicit lifecycle-state filters;
- validation of filter values against existing execution states;
- interaction between filtering and M46 sequence-cursor pagination;
- deterministic ascending sequence ordering;
- API/application contract tests;
- dashboard consumption of the same read model if accepted.

## 5. Out of Scope

- history mutation;
- history deletion or retention;
- event replay/event sourcing;
- cross-execution queries;
- actor/user filtering;
- free-text search over transition reasons;
- arbitrary client-controlled ordering;
- new authentication/authorization;
- lifecycle transition changes;
- new persistence source.

## 6. Alternatives

### A. Keep filtering client-side

Pros: no application or persistence changes. Cons: transfers unnecessary history and duplicates filtering logic across consumers.

### B. Filter by to_state only

Pros: simple and directly useful for terminal/recovery-state inspection. Cons: cannot directly isolate a transition direction.

### C. Filter by from_state and to_state

Pros: precise lifecycle-transition queries; both values already exist in persisted history. Cons: slightly larger API surface.

### D. Filter by transition reason text

Pros: potentially useful for diagnostics. Cons: reason is free-form operational text, so matching semantics become a new unstable contract and clients may depend on diagnostic wording.

## 7. Proposed Direction

The preferred candidate is typed lifecycle filtering using optional `from_state` and `to_state` parameters.

The filter should be applied by the persistence query before pagination so the cursor advances over the filtered sequence rather than over discarded records.

Ordering remains ascending by persisted sequence. No reason-text filtering is proposed for M47.

This is a design candidate, not an implementation authorization.

## 8. Open Questions

1. Should M47 accept both `from_state` and `to_state`, or only `to_state`?
2. If both are supplied, should they be ANDed as an exact transition filter?
3. Should filter names use the API's existing lowercase state values or expose enum names?
4. Should filtered pagination use the same opaque sequence cursor as M46?
5. What should happen when a valid filter matches no history items?
6. Should dashboard filtering be included in the MVP or remain API-only?
7. Is the existing primary key (execution_id, sequence) sufficient for filtered queries, or is a secondary index needed after evidence?
8. Should complete-history compatibility remain unchanged when no filters are supplied?

## 9. Proposed Invariants

- persisted sequence remains the sole ordering authority;
- filtering is read-only;
- filters never mutate or rewrite lifecycle history;
- one execution remains the query scope;
- filter values are explicitly validated;
- pagination cursor semantics remain deterministic;
- existing M45 complete-history behavior remains unchanged when filters are absent;
- ownership authorization remains identical to M45/M46;
- no client-side reconstruction of lifecycle transitions is required;
- transition-reason wording is not a stable filtering contract.

## 10. TDD Acceptance Shape

If the design is accepted, tests should cover at minimum:

- no filters preserves M46 behavior;
- filtering by valid `to_state`;
- filtering by valid `from_state`;
- combined `from_state` + `to_state`;
- invalid state values;
- filter matching no records;
- filtered ordering by persisted sequence;
- filtered pagination with continuation cursor;
- cursor stability across repeated reads;
- empty history;
- unknown execution;
- owner/global authorization;
- another-user rejection;
- restart preserving filtered results;
- reads do not mutate workflow state;
- API transport maps filters without reconstructing history.

## 11. Accepted Decision

M47 is accepted as a narrow read-side extension of the existing M45/M46 lifecycle-history capability.

### Filter contract

The query accepts optional typed `from_state` and `to_state` filters.

- Each value uses the API's existing lowercase lifecycle-state representation.
- If both are supplied, they use AND semantics and represent an exact transition match.
- If only one is supplied, only that transition endpoint is constrained.
- Invalid state values are rejected explicitly.
- A valid filter matching no records returns an empty page, not an error.
- Free-text transition-reason filtering is deferred.

### Pagination and cursor safety

Filtering is applied in the persistence query before pagination.

The existing opaque sequence cursor remains the pagination mechanism. A continuation cursor is bound to the effective query shape, including the active filter values, so a cursor cannot silently be reused against a different filter.

Ordering remains ascending by persisted sequence.

### Compatibility

When no filters are supplied, M45/M46 complete-history behavior remains unchanged.

Ownership authorization remains exactly the existing owner-or-global boundary. The capability remains read-only and scoped to one execution.

### Persistence and indexing

The existing lifecycle-history persistence source remains authoritative. No new persistence schema or mandatory index is introduced in the MVP. Query performance is measured through tests/evidence before adding an index.

### Presentation scope

M47 exposes the filtering capability through the existing application and HTTP read boundary. The dashboard consumes the same API contract; it does not implement filtering locally or reconstruct lifecycle transitions.

### Explicitly deferred

- reason-text filtering;
- cross-execution queries;
- lifecycle mutation/replay;
- retention/deletion;
- analytics/aggregation;
- new authorization semantics;
- arbitrary ordering;
- new persistence sources.

## 12. TDD Acceptance Criteria

The implementation must cover at minimum:

- omitted filters preserve M46 behavior;
- valid `to_state` filtering;
- valid `from_state` filtering;
- combined `from_state` + `to_state` exact-transition filtering;
- invalid state values;
- valid filters with no matches;
- filtered results remain ascending by persisted sequence;
- first-page filtering;
- continuation pagination over filtered results;
- cursor reuse with different filters is rejected;
- empty history;
- unknown execution;
- owner/global authorization;
- another-user rejection;
- restart consistency;
- filtered reads do not mutate workflow state;
- API transport passes filter values through without reconstructing history.

## 13. Design Gate Decision

**Status: Accepted — M47 implementation is authorized within the scope above.**

The implementation must extend the existing history read capability rather than create a second query path.

