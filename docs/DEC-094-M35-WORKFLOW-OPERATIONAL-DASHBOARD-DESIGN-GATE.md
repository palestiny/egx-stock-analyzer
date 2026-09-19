# DEC-094 — M35 Scheduled Workflow Operational Dashboard Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M35 — Scheduled Workflow Operational Dashboard

## 1. Problem

M33 established a provider-neutral application read capability for scheduled workflow executions, and M34 exposed that capability through:

```
GET /api/v1/workflows/executions
```

The project dashboard currently exposes stock analysis, market opportunities, history, comparison, and performance views, but it does not expose the operational state of scheduled workflows.

Users therefore cannot see whether scheduled occurrences are running, completed, failed, or interrupted from the existing dashboard.

M35 should add a presentation-only operational view that consumes the M34 API without introducing workflow control or duplicated business logic.

## 2. Desired Outcome

Add a dashboard section for scheduled workflow operational visibility that:

1. loads persisted workflow executions from the M34 API;
2. presents newest executions first using the API's ordering;
3. displays occurrence ID, lifecycle state, created/updated timestamps, analysis state, and delivery state;
4. supports filtering by exact occurrence ID;
5. distinguishes loading, empty, unavailable, and transport-error states;
6. never calculates workflow state or outcome semantics locally;
7. never starts, recovers, cancels, retries, or mutates a workflow.

## 3. Boundary

```
React Dashboard
      ↓
frontend API client
      ↓
GET /api/v1/workflows/executions
      ↓
FastAPI
      ↓
GetScheduledWorkflowExecutions
```

The dashboard remains a presentation client.

## 4. Proposed UI Slice

A dedicated **Scheduled Workflows** panel should contain:

- heading and short operational description;
- optional occurrence-ID filter;
- refresh/load action;
- execution rows/cards;
- lifecycle state;
- occurrence ID;
- created timestamp;
- updated timestamp;
- analysis state;
- delivery state.

Each row is read-only.

No workflow control buttons are included in M35.

## 5. Data Contract

The dashboard consumes the M34 response:

```json
{
  "items": [
    {
      "id": "uuid",
      "occurrence_id": "string",
      "state": "completed",
      "created_at": "ISO-8601",
      "updated_at": "ISO-8601",
      "analysis_state": "completed",
      "delivery_state": "completed"
    }
  ]
}
```

The frontend must not derive a replacement state from timestamps or analysis/delivery values.

## 6. User-State Semantics

### Loading

Display an explicit loading state while the request is pending.

### Empty

Display a neutral empty state when `items` is empty.

### Filtered Empty

Display that no execution matches the entered occurrence ID.

### Unavailable

If the API returns 503, display that scheduled workflow visibility is not configured.

### Transport Error

Display a generic request failure without exposing backend exception details.

The dashboard must not infer workflow failure from an HTTP transport error.

## 7. Scope

### In scope

- frontend API client method;
- dashboard operational panel;
- occurrence-ID filter;
- loading/empty/unavailable/error states;
- component/API tests;
- presentation-only formatting of timestamps.

### Explicitly out of scope

- workflow start/recovery/retry/cancel controls;
- scheduler configuration;
- workflow mutation;
- automatic refresh timers;
- WebSocket/SSE real-time updates;
- pagination;
- authentication/authorization UI;
- metrics/tracing;
- notifications;
- analytical calculations;
- trading behavior.

## 8. Alternatives

### A — Add operational data to the existing stock-analysis panel

Rejected because workflow lifecycle is a separate operational concern and would make the stock analysis view responsible for unrelated workflow state.

### B — Build a separate dashboard route/page

Deferred. The current frontend is a single application surface; a dedicated panel is sufficient for the MVP and avoids premature routing complexity.

### C — Add workflow controls to the panel

Rejected for M35. Visibility and control have different safety and authorization requirements.

### D — Poll automatically

Deferred. M35 should first establish a correct read-only view. Automatic refresh requires a separate freshness and load decision.

## 9. Open Questions

1. Should the panel show a fixed number of latest executions or all API results?
2. Should timestamps use the browser's local timezone or a project-defined timezone?
3. Should lifecycle states receive presentation labels distinct from persisted enum values?
4. Should the occurrence filter be applied on each request or only when the user submits the form?
5. Should the operational panel load automatically on dashboard startup or only after an explicit user action?
6. Should the panel be shown when the workflow feature is unavailable (503), or hidden behind an unavailable-state message?

## 10. Proposed Invariants

1. The dashboard never owns workflow business semantics.
2. The dashboard never mutates workflow state.
3. The dashboard never starts or recovers a workflow.
4. The dashboard consumes the M34 API contract only.
5. API ordering is preserved; the dashboard does not reorder executions.
6. Empty results are not treated as errors.
7. HTTP errors are not converted into inferred workflow states.
8. No analytical score or trading decision is introduced.
9. The panel remains independently testable.
10. M35 introduces no new backend persistence.

## 11. TDD Acceptance Shape

Before implementation is authorized, tests should establish:

- API client calls the correct endpoint;
- filter is passed correctly;
- successful executions render in API order;
- lifecycle and outcome fields render without recalculation;
- loading state is visible;
- empty state is visible;
- 503 unavailable state is visible;
- transport error state is visible;
- changing the filter does not mutate existing workflow data;
- no workflow-control action is triggered by the dashboard.

## 12. Design Gate Decision

**Status: Proposed — implementation is not authorized yet.**

Resolve the open questions and accept this presentation boundary before implementation.

## 13. Revisit Conditions

Revisit this gate if:

- workflow control becomes a user requirement;
- real-time visibility becomes necessary;
- pagination/retention changes the M34 API contract;
- authentication/multi-user visibility becomes required;
- the dashboard architecture changes materially.
