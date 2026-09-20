# M36 — Scheduled Workflow Recovery Control MVP Completion

**Status:** Complete  
**Date:** 2026-09-19  
**Design Gate:** `docs/DEC-095-M36-SCHEDULED-WORKFLOW-RECOVERY-CONTROL-DESIGN-GATE.md`  
**Implementation PR:** #67  
**Implementation head:** `06b671937a9730ead07793cc6cd9acd4c62dc2a9`

## Delivered

M36 adds an explicit operator-triggered recovery command for one persisted `INTERRUPTED` scheduled workflow execution.

### Application

- Reuses the existing M31 `RecoverDurableScheduledWorkflow` capability.
- Preserves the existing scheduled workflow execution identity.
- Does not create a replacement occurrence.
- Accepts only `INTERRUPTED` executions.
- Keeps recovery synchronous, sequential, and explicit.

### HTTP

`POST /api/v1/workflows/executions/{execution_id}/recover`

Transport semantics:

- `200` — recovery completed and the resulting persisted workflow execution is returned.
- `404` — execution does not exist.
- `409` — execution exists but is not currently recoverable.
- `503` — recovery capability is not configured.
- `500` — unexpected recovery failure, using the existing safe error pattern.

### Dashboard

The scheduled-workflow operational panel now:

- shows Recover only for `INTERRUPTED` rows;
- disables only the clicked row while recovery is pending;
- updates the row directly from the successful POST response;
- presents explicit user-safe states for 404, 409, and unexpected failures;
- does not introduce polling or implicit recovery.

## TDD Coverage

Backend coverage verifies:

- successful delegation and response mapping;
- missing execution → 404;
- non-recoverable execution → 409;
- unconfigured recovery → 503.

Frontend coverage verifies:

- POST recovery request;
- Recover visibility only for interrupted rows;
- successful row replacement;
- explicit conflict handling.

## CI Validation

GitHub Actions **Run #1043** completed successfully for `06b671937a9730ead07793cc6cd9acd4c62dc2a9`:

- Python unit tests: success
- Frontend tests: success
- Frontend production build: success

The implementation also required one CI-driven composition correction and one dashboard test assertion correction before reaching the green run. The final green run is the authoritative validation.

## Deferred

- authentication/authorization;
- bulk recovery;
- concurrent recovery;
- automatic polling;
- asynchronous recovery;
- retry policy changes;
- workflow cancellation;
- replacement occurrence creation;
- new persistence schema;
- changes to M31 recovery semantics.

## Milestone Result

M36 is complete. The project can now move to a new design gate rather than expanding recovery behavior opportunistically.
