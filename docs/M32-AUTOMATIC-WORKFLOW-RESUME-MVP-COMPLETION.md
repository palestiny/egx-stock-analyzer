# M32 — Automatic Scheduled Workflow Resume MVP Completion

**Status:** Complete  
**Date:** 2026-09-19  
**Design Gate:** `docs/DEC-091-M32-AUTOMATIC-WORKFLOW-RESUME-DESIGN-GATE.md`  
**Implementation PR:** #58

## Delivered

M32 adds startup-triggered automatic recovery for persisted `INTERRUPTED` scheduled workflow executions.

The implementation:

- discovers only persisted `INTERRUPTED` executions;
- orders recovery deterministically by occurrence identity and execution ID;
- delegates each recovery to the accepted M31 recovery capability;
- derives the original analysis date from the persisted occurrence identity;
- preserves the original scheduled workflow execution UUID;
- isolates individual recovery failures so later executions are still attempted;
- surfaces durable-store inspection failure as an application startup failure;
- triggers recovery from the application lifecycle rather than the scheduler or HTTP layer;
- keeps recovery sequential and process-local.

## Boundary

```
Application Startup
      ↓
AutomaticWorkflowRecovery
      ↓
ScheduledWorkflowExecutionStore
      ↓
M31 Recovery Capability
      ↓
M29 Scheduled Analysis + Delivery Workflow
```

## Validation

GitHub Actions Run #937 completed successfully for implementation head `273d34f29af17341ce507b0e04c03e501c0fa138`.

Validated CI includes:

- Python unit tests: success
- Frontend tests: success
- Frontend production build: success

Additional focused coverage validates deterministic interrupted-execution discovery, startup lifecycle invocation, failure isolation, malformed occurrence handling, and SQLite persistence across restart.

## Deferred

M32 does not introduce:

- automatic replay of non-INTERRUPTED executions;
- step-level checkpoints;
- distributed locks/workers;
- parallel recovery;
- queues;
- provider retry;
- new notification channels;
- recovery HTTP endpoints;
- user-configurable recovery policies;
- trading, portfolio allocation, or AI decisions.
