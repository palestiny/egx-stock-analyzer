# DEC-093 — M34 Scheduled Workflow Operational Visibility API Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M34 — Scheduled Workflow Operational Visibility API

## 1. Problem

M33 established a provider-neutral application read capability for persisted scheduled workflow executions:

```
ScheduledWorkflowExecutionStore
          ↓
GetScheduledWorkflowExecutions
          ↓
ScheduledWorkflowExecutionReadModel
```

The capability is currently not exposed through the project's HTTP boundary.

Operational consumers therefore cannot inspect scheduled workflow lifecycle state through the same API surface used by the rest of the application.

M34 should expose the existing read capability without moving workflow or persistence semantics into FastAPI.

## 2. Desired Outcome

Add a read-only HTTP endpoint that exposes the M33 read model through a stable transport contract.

The endpoint should:

1. return persisted scheduled workflow executions;
2. preserve M33 deterministic ordering;
3. support the existing exact occurrence filter;
4. expose lifecycle and persisted outcome information without recalculation;
5. map application/infrastructure failures to the project's safe API error boundary;
6. remain read-only;
7. avoid adding workflow execution, recovery, scheduling, or notification behavior.

## 3. Proposed Boundary

```
HTTP
  ↓
Scheduled Workflow Execution API
  ↓
GetScheduledWorkflowExecutions
  ↓
ScheduledWorkflowExecutionStore
```

FastAPI owns transport validation and serialization only.

The M33 application capability remains the owner of selection and read-model composition.

## 4. Proposed HTTP Contract

### Endpoint

```
GET /api/v1/workflows/executions
```

### Optional filter

```
GET /api/v1/workflows/executions?occurrence_id=<exact-occurrence-id>
```

The filter is passed unchanged to the M33 application capability.

### Success response

HTTP 200 with an array:

```json
[
  {
    "id": "uuid",
    "occurrence_id": "2026-09-19T09:00:00+03:00",
    "state": "completed",
    "created_at": "2026-09-19T09:00:00+03:00",
    "updated_at": "2026-09-19T09:01:12+03:00",
    "analysis_state": "completed",
    "delivery_state": "completed"
  }
]
```

An empty result is HTTP 200 with `[]`.

Enum values use their existing persisted string values. Timestamps remain ISO-8601 transport values.

## 5. Failure Semantics

The endpoint is read-only and should not invent domain failures.

- no matching occurrence → HTTP 200 with `[]`;
- invalid query input, if any transport-level validation is required → HTTP 422 using FastAPI's normal validation behavior;
- unexpected application/infrastructure failure → HTTP 500 with the project's existing safe error response pattern;
- persistence details and exception messages must not become the HTTP contract.

No 404 is introduced for an empty operational-history query.

## 6. Scope

### In scope

- FastAPI route;
- response DTO/read model mapping;
- optional exact `occurrence_id` query parameter;
- API contract tests;
- application-runtime composition required to make the M33 capability available to the HTTP layer;
- safe error handling consistent with existing API boundaries.

### Explicitly out of scope

- workflow execution or recovery endpoints;
- workflow mutation;
- retry/replay;
- scheduler control;
- notification delivery;
- dashboard UI;
- authentication/authorization;
- pagination;
- retention;
- real-time streaming;
- metrics/tracing;
- filtering by fields not already supported by M33;
- new persistence schema.

## 7. Alternatives

### A — Read SQLite directly from FastAPI

Rejected because it violates the existing application/infrastructure boundary and duplicates M33 read semantics.

### B — Expose M33 read model directly as a framework response model

Possible, but the HTTP layer should own its transport DTO so the application read model remains independent from FastAPI/Pydantic.

### C — Add an operational dashboard first

Deferred. The API is the reusable transport boundary; dashboard presentation can consume it later through a separate UI decision.

### D — Add workflow mutation endpoints alongside the read endpoint

Rejected for M34 because operational visibility and workflow control have different risk and authorization requirements.

## 8. Accepted Decisions

1. **Route:** Use `GET /api/v1/workflows/executions`. This names the operational resource directly and leaves workflow mutation endpoints separate.
2. **Response shape:** Return an envelope `{"items": [...]}`. The existing API already uses named response objects for collection reads, and the envelope leaves room for future pagination metadata without changing the resource from an array to an object later.
3. **Occurrence filter:** Accept an optional exact non-empty `occurrence_id`. Blank values are treated as invalid transport input rather than as an unfiltered query.
4. **Single-execution lookup:** Defer UUID lookup. M34 keeps one list/filter read contract; a direct execution resource can be introduced later if a concrete client need appears.
5. **Runtime composition:** Add the read capability to the infrastructure composition as an optional application capability exposed to FastAPI. The API must not construct persistence objects itself.
6. **Availability:** Compose the scheduled-workflow execution store and read capability independently of optional Telegram delivery configuration. This makes historical workflow visibility available even when notification delivery is not configured, without changing workflow execution behavior.
7. **State representation:** Preserve existing lowercase enum values through the transport DTO. No second transport-specific state vocabulary is introduced.
8. **Error handling:** Empty history and non-matching filters return HTTP 200 with an empty `items` collection. Unexpected application/infrastructure failures use the existing safe HTTP 500 pattern. The endpoint does not expose persistence exception details.

## 9. Proposed Invariants

1. GET never mutates workflow state.
2. GET never executes or recovers a workflow.
3. GET never triggers analysis or notification delivery.
4. M33 remains the owner of ordering and occurrence filtering semantics.
5. FastAPI never reads SQLite directly.
6. Persistence exceptions are not exposed as internal error details.
7. Empty history is a successful response.
8. The API does not create a second source of truth.
9. Dashboard behavior is not introduced as part of M34.
10. Authentication remains deferred unless a concrete multi-user requirement appears.

## 10. TDD Acceptance Shape

Before implementation is authorized, tests should establish at least:

- empty history returns HTTP 200 and `[]`;
- multiple executions preserve M33 newest-first ordering;
- occurrence filter returns only the matching execution;
- missing occurrence filter match returns HTTP 200 and `[]`;
- response preserves execution/occurrence IDs;
- response preserves lifecycle, timestamps, analysis, and delivery state;
- store/application failure returns the safe HTTP 500 contract;
- GET does not mutate persisted state;
- endpoint does not execute, recover, schedule, or notify workflows;
- API remains available independently of optional notification-provider configuration if the existing runtime composition permits it.

## 11. Design Gate Decision

**Status: Accepted — implementation is authorized for the M34 HTTP read capability defined here.**

## 12. Revisit Conditions

Revisit this gate if:

- M33's application read model changes;
- authentication becomes mandatory;
- operational visibility requires real-time streaming;
- pagination/retention becomes necessary;
- workflow control is introduced;
- the existing API versioning strategy changes materially.
