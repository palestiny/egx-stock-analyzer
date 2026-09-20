# DEC-114 — M52 Analysis Run Discovery Dashboard Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M52 — Analysis Run Discovery Dashboard

## Context

M51 introduced the authenticated `ListAnalysisRuns` application/API capability for discovering persisted analysis runs.

The dashboard currently has access to M50 single-run detail, but M51 intentionally deferred a dashboard discovery surface. Users therefore need a presentation-level path from "I know a run ID" to "I can discover and select an analysis run."

This gate is presentation-only. It must consume the existing M51 HTTP contract and must not move query, pagination, authentication, or analysis semantics into React.

## Desired Outcome

Introduce a dashboard surface that can:

1. discover persisted analysis runs through the existing M51 API;
2. show only the run-level metadata exposed by M51;
3. support the server-side state filter and cursor pagination;
4. let the user select a run and navigate to the existing M50 run detail;
5. preserve authenticated API boundaries;
6. make loading, empty, invalid-query, and transport-error states explicit;
7. remain responsive without introducing mobile-specific application logic.

## Scope

### In Scope

- run discovery presentation;
- run list item presentation;
- aggregate-state filter control;
- bounded pagination controls;
- navigation from a run item to M50 detail;
- loading/empty/error states;
- frontend API-client boundary;
- frontend tests and accessibility behavior;
- responsive layout for existing web dashboard.

### Explicitly Out of Scope

- changing M51 API semantics;
- changing AnalysisRunStore or persistence;
- creating new run data in the frontend;
- client-side sorting/filtering of the authoritative run set;
- analysis execution;
- rerunning an analysis from the discovery screen;
- automatic polling/real-time updates;
- per-user run ownership;
- ranking or opportunity calculations;
- new mobile application architecture.

## Architectural Boundary

The intended flow is:

```
Dashboard Run Discovery
        ↓
frontend API client
        ↓
GET /api/v1/analysis-runs
        ↓
ListAnalysisRuns
        ↓
AnalysisRunStore
```

The dashboard owns presentation state only. M51 remains authoritative for filtering, ordering, pagination, authentication, and run metadata.

## Alternatives Considered

### A — Add a Run Discovery Panel to the Existing Dashboard

**Advantages**
- minimal navigation change;
- reuses the current dashboard shell;
- lower implementation surface.

**Trade-offs**
- increases density of the existing dashboard;
- can mix current-analysis and historical-run concepts;
- may become harder to extend if run discovery grows into a richer workflow.

**Assessment:** Candidate for MVP.

### B — Create a Dedicated Analysis Runs Page/Route

**Advantages**
- clear separation between current analysis and historical run discovery;
- gives pagination/filtering enough space;
- easier future extension toward richer run browsing.

**Trade-offs**
- introduces navigation structure and another page;
- slightly larger frontend change.

**Assessment:** Candidate for MVP.

### C — Keep Run Discovery Out of the Dashboard

**Advantages**
- no frontend work;
- preserves the current dashboard surface.

**Trade-offs**
- leaves M51 primarily useful through direct API access;
- makes selecting an existing run inconvenient for normal users.

**Assessment:** Valid deferral, but it leaves the M51 read capability without a first-class user-facing discovery path.

## Open Questions

These must be resolved before implementation:

1. **Surface:** existing dashboard panel or dedicated route/page?
2. **Pagination UX:** numbered/previous-next controls or only a "load next" interaction around the opaque cursor?
3. **State filter:** single-select state filter or an "all" default with one active state at a time?
4. **Run detail navigation:** route-based navigation to the existing M50 detail or an in-place detail transition?
5. **Refresh semantics:** explicit refresh only, or refresh after returning from detail?
6. **Metadata density:** show created time + state only, or also requested/successful/failed counts if the API exposes them in a future revision?
7. **Error semantics:** how should 401/403, 400 invalid query, and transport failures be presented without exposing server internals?
8. **Responsive behavior:** how should filters and pagination collapse on narrow screens?

## Proposed Invariants

1. React never reproduces M51 ordering or filtering logic.
2. The cursor is treated as opaque.
3. The dashboard never reads persistence directly.
4. Authentication remains owned by the existing frontend session/API boundary.
5. M50 run-detail behavior remains unchanged.
6. A no-match response is rendered as an empty state, not an error.
7. API errors are mapped to user-safe presentation states.
8. No analysis execution is triggered by merely browsing runs.
9. No automatic polling is introduced without a separate decision.
10. Frontend tests cover every authoritative UI state.

## TDD Acceptance Shape

Before implementation, tests should establish at least:

- successful first-page rendering;
- state-filter request propagation without client-side filtering;
- next-page navigation using the opaque cursor;
- no-more-pages behavior;
- empty result state;
- authenticated-session failure state;
- invalid-query/transport error state;
- selecting a run navigates to the existing M50 detail surface;
- loading state;
- responsive/accessibility-critical controls.

## Design Gate Status

**Proposed — implementation is not authorized by this document yet.**

The next action is to resolve the open questions and record the accepted presentation decision before implementing the M52 dashboard slice.
