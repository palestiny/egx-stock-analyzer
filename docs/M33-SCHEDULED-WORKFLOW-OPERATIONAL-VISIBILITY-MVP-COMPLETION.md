# M33 — Scheduled Workflow Operational Visibility MVP Completion

**Status:** Complete  
**Date:** 2026-09-19  
**Design Gate:** `docs/DEC-092-M33-SCHEDULED-WORKFLOW-OPERATIONAL-VISIBILITY-DESIGN-GATE.md`  
**Implementation PR:** #60

## Delivered

M33 adds a provider-neutral, read-only application capability for inspecting persisted scheduled workflow executions.

The implementation:

- exposes all persisted scheduled workflow executions through an application read model;
- orders history deterministically by `created_at DESC, execution_id DESC`;
- supports an exact optional `occurrence_id` filter;
- preserves execution identity and occurrence identity;
- preserves lifecycle, analysis, delivery, and timestamp fields already persisted by the workflow model;
- keeps persistence behind `ScheduledWorkflowExecutionStore`;
- introduces no new persistence schema;
- does not change workflow execution, recovery, scheduling, notification, or analytical behavior;
- propagates store failures rather than converting infrastructure failures into empty history.

## Boundary

```
ScheduledWorkflowExecutionStore
          ↓
GetScheduledWorkflowExecutions
          ↓
ScheduledWorkflowExecutionReadModel
```

HTTP and dashboard exposure remain deferred to a separate transport design gate.

## Validation

GitHub Actions Run #963 completed successfully for implementation head `fd519751b69909ac8203cb3f39fd7ccc9dafc5da`.

Validated CI includes:

- Python unit tests: success
- Frontend tests: success
- Frontend production build: success

Focused M33 coverage validates empty history, single persisted execution, deterministic newest-first ordering, lifecycle/outcome preservation, exact occurrence filtering, missing-filter behavior, read-only behavior, and store failure propagation.

## Deferred

M33 does not introduce:

- HTTP endpoints;
- dashboard changes;
- real-time streaming;
- workflow replay or recovery behavior;
- scheduler behavior;
- notification delivery changes;
- authentication/authorization;
- pagination or retention policy;
- metrics/tracing;
- distributed execution;
- a second operational data store.
