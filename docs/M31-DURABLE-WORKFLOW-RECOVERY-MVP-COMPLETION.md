# M31 — Durable Workflow Recovery MVP Completion Record

**Milestone:** M31  
**Status:** Complete  
**Implementation:** PR #56  
**Merge commit:** `3e5a0607389abc75f4c91f2e27913f9cb4cbfef1`  
**Implementation head validated by GitHub Actions:** `3a4fbc96f00dbc57ec5a929c8f2437df42ffc80d` (Run #899, success)

## Outcome

M31 adds an explicit application-level recovery capability for one persisted `INTERRUPTED` scheduled workflow execution.

Recovery reuses the existing workflow execution identity and the existing M29 workflow. It does not create a new scheduled occurrence and does not introduce automatic startup replay.

## Implemented Boundary

```
Persisted INTERRUPTED Workflow Execution
              ↓
RecoverDurableScheduledWorkflow
              ↓
Existing Durable Scheduled Workflow
              ↓
Existing Analysis + Automatic Alert Delivery
```

The recovery capability:

- accepts one persisted interrupted workflow execution;
- validates that the execution is recoverable;
- transitions it through the existing lifecycle;
- reuses the existing workflow identity;
- preserves existing analysis-result persistence and alert-delivery idempotency;
- preserves workflow failure semantics;
- remains sequential and process-local.

## Verification

Focused M31 unit and integration tests were added. GitHub Actions Run #899 passed on the final implementation head before merge.

No claim is made about local terminal execution.

## Deferred

The following remain outside M31:

- automatic startup replay;
- step-level checkpoints;
- partial workflow resume;
- distributed coordination;
- queues/workers;
- new provider retry policies;
- multi-process recovery;
- new HTTP recovery endpoint.

## Source of Truth

The accepted design is documented in `docs/DEC-090-M31-DURABLE-WORKFLOW-RECOVERY-DESIGN-GATE.md`.

