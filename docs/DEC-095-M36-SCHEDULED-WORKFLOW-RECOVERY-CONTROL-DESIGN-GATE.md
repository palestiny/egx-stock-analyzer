# DEC-095 — M36 Scheduled Workflow Recovery Control Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M36 — Scheduled Workflow Recovery Control

## 1. Problem

M30–M32 established durable scheduled-workflow lifecycle and recovery capabilities. M33–M35 made that operational state visible through the application, API, and dashboard.

The current system can automatically recover eligible interrupted executions during startup, and it can recover one interrupted execution through an existing application capability. However, the dashboard remains read-only: an operator cannot explicitly request recovery for a specific interrupted execution.

The next controlled capability is an explicit operator-triggered recovery boundary, without moving workflow semantics into React or the HTTP layer.

## 2. Desired Outcome

M36 should allow an operator to explicitly request recovery of one persisted INTERRUPTED scheduled workflow execution.

It should verify existence and recoverability, delegate to the existing RecoverDurableScheduledWorkflow capability, preserve the existing execution identity, expose the resulting persisted state, and provide an explicit non-GET HTTP command plus a dashboard action.

## 3. Boundary

React Dashboard → POST recovery command → FastAPI → RecoverDurableScheduledWorkflow → RunDurableScheduledWorkflow.recover → ScheduledWorkflowExecutionStore

The dashboard remains a presentation/control client. It does not transition workflow state itself.

## 4. Scope

In scope: explicit recovery command, HTTP contract, dashboard recovery action for interrupted executions, explicit success/not-found/not-recoverable/error states, reuse of M31 recovery, and application/API/dashboard tests.

Out of scope: canceling workflows, arbitrary new workflow starts, retrying terminal failures, scheduler configuration, automatic polling, real-time streaming, bulk recovery, concurrent recovery, authentication implementation, new recovery persistence schema, new retry policy, or changes to M31 recovery semantics.

## 5. Alternatives

### A — Keep recovery application-only

Smallest surface and lowest operational risk, but operators cannot recover a specific interrupted execution on demand.

### B — Dedicated recovery HTTP command and dashboard action

Explicit control boundary, reusable outside the dashboard, and easy to test. Adds a mutating endpoint and UI state.

**Assessment:** preferred candidate.

### C — Put recovery logic directly in the dashboard/API handler

Rejected because it duplicates application semantics and weakens the existing M31 boundary.

### D — Recover automatically when the dashboard opens

Rejected because a visibility surface should not perform implicit mutation.

## 6. Proposed Command Contract

Candidate endpoint: POST /api/v1/workflows/executions/{execution_id}/recover

Success returns the resulting scheduled workflow execution. Missing execution returns 404. Existing but non-INTERRUPTED execution returns 409. Unexpected failures use the existing safe 500 pattern.

The command is synchronous and never creates a replacement occurrence or changes the execution UUID.

## 7. Dashboard Behavior

INTERRUPTED rows show an explicit Recover action. Other states show no recovery action.

Success updates the row from the command response. 404, 409, and transport failures have explicit user-visible states without exposing backend exception details.

No automatic polling or refresh timer is introduced.

## 8. Safety Invariants

1. Only INTERRUPTED executions are recoverable.
2. Recovery reuses the existing execution identity.
3. Recovery never creates a replacement occurrence.
4. HTTP delegates to the M31 application capability.
5. Dashboard state is never used to perform lifecycle transitions.
6. GET visibility remains side-effect free.
7. Recovery is explicit and user-triggered.
8. Existing M31 analysis and delivery idempotency remains authoritative.
9. No new retry layer is introduced.
10. Recovery remains single-execution and sequential.

## 9. TDD Acceptance Shape

- interrupted execution can be recovered;
- missing execution maps to not-found;
- non-interrupted execution is rejected;
- execution identity is preserved;
- M31 recovery capability is delegated to;
- HTTP recovery uses POST and the execution UUID path;
- successful recovery returns the persisted workflow model;
- dashboard shows Recover only for interrupted rows;
- dashboard handles success, 404, 409, and transport failure;
- no new occurrence is created.

## 10. Open Decisions

1. Use 409 Conflict for a non-recoverable execution, or another explicit 4xx status?
2. Inline Recover action per interrupted row, or a separate selected-execution action area?
3. After success, update the row immediately from the command response, or require explicit reload?
4. Disable only the clicked row while recovery is pending, or all recovery actions?
5. Keep M36 unauthenticated because authentication does not yet exist, or block the feature until an auth boundary exists?

## 11. Resolved Decisions

1. **Non-recoverable execution status:** use **409 Conflict**. The execution exists, but its current lifecycle state conflicts with the recovery command.
2. **Dashboard action placement:** use an **inline Recover action on each INTERRUPTED row**. This keeps the operator's target explicit and avoids a second selection state.
3. **Post-success UI state:** **update the row immediately from the command response**. No extra GET is required after a successful recovery.
4. **Pending state:** **disable only the clicked row's Recover action**. Other interrupted executions remain independently actionable.
5. **Authentication:** M36 proceeds **without authentication**, because no authentication boundary exists yet. This is an explicit current-system constraint, not a claim that recovery is safe for an authenticated multi-user production environment. Authentication remains a prerequisite before exposing this control to a multi-user deployment.

## 12. Accepted Design

**Status: Accepted — implementation is authorized for the M36 MVP defined here.**

The accepted boundary is:

```
React Dashboard
      ↓
POST /api/v1/workflows/executions/{execution_id}/recover
      ↓
RecoverScheduledWorkflowExecution
      ↓
RecoverDurableScheduledWorkflow
      ↓
RunDurableScheduledWorkflow.recover
      ↓
ScheduledWorkflowExecutionStore
```

The endpoint is a synchronous, explicit command. Only INTERRUPTED executions are eligible. A missing execution returns 404; an existing non-INTERRUPTED execution returns 409; successful recovery returns the resulting persisted workflow execution; unexpected failures follow the existing safe 500 pattern.

The dashboard renders Recover inline only for INTERRUPTED rows, disables only the clicked row while pending, and replaces that row with the successful command response. It exposes explicit user-safe states for 404, 409, and transport failures. GET visibility remains side-effect free.

No new occurrence, retry layer, persistence schema, recovery semantics, scheduler behavior, or authentication implementation is introduced.

## 13. TDD Acceptance Criteria

- interrupted execution can be recovered;
- missing execution maps to 404;
- non-interrupted execution maps to 409;
- execution identity is preserved;
- M31 recovery capability is delegated to;
- HTTP recovery uses POST and the execution UUID path;
- successful recovery returns the persisted workflow model;
- dashboard shows Recover only for interrupted rows;
- only the clicked dashboard row is disabled while pending;
- dashboard updates the recovered row directly from the command response;
- dashboard handles 404, 409, and transport failure;
- no new occurrence is created.

## 14. Design Gate Status

**Accepted — implementation is authorized.**

## 15. Revisit Conditions

Revisit if workflow recovery semantics change, authentication becomes mandatory, recovery becomes asynchronous, bulk recovery becomes necessary, the dashboard architecture changes materially, or step-level checkpoints are introduced.