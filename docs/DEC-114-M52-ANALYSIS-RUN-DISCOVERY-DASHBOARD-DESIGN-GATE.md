# DEC-114 — M52 Analysis Run Discovery Dashboard Design Gate

**Status:** Accepted  
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

## Accepted Decisions

### 1. Surface

M52 uses a dedicated **Analysis Runs page/route** rather than another panel inside the already dense stock-analysis dashboard.

**Trade-off:** this adds a small navigation surface, but keeps run discovery separate from current-stock analysis and gives pagination/filtering room to evolve without further increasing dashboard density.

### 2. Pagination UX

The MVP uses explicit **Previous/Next** controls where a previous cursor is available, with the server cursor treated as opaque. The UI also provides a clear first-page action when the user has navigated forward.

The frontend does not derive offsets, decode cursors, or reproduce server pagination rules.

### 3. State Filter

The filter is a single-select control with **All** as the default and one optional persisted aggregate state at a time.

The selected value is sent to M51 as-is. The frontend never filters an already-returned page.

### 4. Run Detail Navigation

Selecting a run navigates to the existing M50 detail surface using a route-based URL containing the AnalysisRunId.

The M50 detail capability and API contract remain unchanged.

### 5. Refresh Semantics

Refresh is explicit. Returning from M50 detail does not silently trigger a new discovery request.

This keeps navigation deterministic and avoids hidden network activity.

### 6. Metadata Density

The discovery list shows only M51's authoritative run metadata:

- AnalysisRunId;
- created timestamp;
- aggregate execution state.

Requested/successful/failed counts are not synthesized in React and are deferred unless the M51 API is explicitly extended by a future decision.

### 7. Error Semantics

The dashboard maps errors to safe presentation states:

- 401 → session-expired/authentication state using the existing frontend session boundary;
- 403 → access-denied state;
- 400 → invalid-query state;
- other non-success responses → generic run-discovery transport failure.

Server internals are not rendered.

### 8. Responsive Behavior

On narrow screens, the state filter and refresh control stack vertically; run metadata remains readable without horizontal scrolling; pagination controls remain individually accessible and wrap when necessary.

No mobile-specific application logic is introduced.

## Accepted Boundary

```
Analysis Runs Page
        ↓
frontend API client
        ↓
GET /api/v1/analysis-runs
        ↓
ListAnalysisRuns
        ↓
AnalysisRunStore
```

The dashboard owns presentation state and navigation only. M51 remains authoritative for ordering, filtering, pagination, authentication, and run metadata.

## TDD Acceptance Criteria

- first page renders server-provided items in server order;
- state filter is propagated to the API without client-side filtering;
- next-page navigation passes the returned opaque cursor unchanged;
- no-more-pages disables the next action;
- first-page navigation clears the cursor;
- empty results render an explicit empty state;
- 401/403/400 and generic transport failures map to safe UI states;
- selecting a run navigates to the M50 detail route;
- loading and refresh states are explicit;
- controls remain keyboard accessible and usable on narrow screens;
- browsing never triggers analysis execution;
- M50 detail behavior remains unchanged.

## Design Gate Status

**Accepted — implementation is authorized for the M52 MVP defined here.**
