# M39 — Multi-User Authentication & Identity Transport MVP Completion

**Milestone:** M39  
**Status:** Complete  
**Date:** 2026-09-19  
**Design Gate:** `docs/DEC-099-M39-MULTI-USER-AUTHENTICATION-DESIGN-GATE.md`

## Outcome

M39 establishes the first concrete transport-to-application identity path for multiple users without moving credentials into domain entities or changing the ownership model established by M38.

The first migrated user-owned capability is scheduled workflow execution visibility and recovery.

## Implemented boundary

```
HTTP Request
    ↓
Configured Bearer Authentication Adapter
    ↓
AuthenticatedIdentity
    ↓
Ownership Authorization Boundary
    ↓
Scheduled Workflow Capability
    ↓
SQLite persistence
```

## Authentication

The infrastructure configuration accepts per-user bearer credentials through `EGX_USER_TOKENS`.

The configured mapping resolves a user UUID to a credential. The authentication adapter checks the durable user lifecycle state on every request:

- ACTIVE → authentication allowed;
- DISABLED → authentication rejected;
- DELETED → authentication rejected;
- missing user → authentication rejected.

Raw credentials do not enter application capability contracts or domain entities.

The existing M37 operator token remains supported as a compatibility credential and resolves only to `LEGACY_OPERATOR_USER_ID`.

## Ownership migration

The following user-owned API/application capabilities now receive the authenticated identity:

- `GET /api/v1/workflows/executions`
- `POST /api/v1/workflows/executions/{execution_id}/recover`

A user can see and recover their own workflow executions.

A user cannot access another user's execution.

Global/system workflow executions remain available only through the operator compatibility identity.

## Transport semantics

The protected workflow surface now has explicit semantics:

- missing/invalid credentials → **401**
- authenticated non-owner → **403**
- missing workflow occurrence/execution → **404**
- non-recoverable workflow execution → **409**
- unconfigured capability → **503**

The health endpoint remains public.

## Compatibility

M37 operator-protected endpoints remain unchanged.

The multi-user adapter is introduced as a replaceable authentication boundary. A future external identity provider can replace the adapter without changing application ownership semantics.

Frontend login/session UX is intentionally deferred.

## Validation

GitHub Actions Run **#1346** completed successfully for the M39 implementation head:

- Python unit tests: **success**
- Frontend tests: **success**
- Frontend production build: **success**
- Python suite: **552 passed, 1 skipped, 1 deselected**

The implementation was merged through **PR #81**.

## Deferred

M39 does not include:

- external identity-provider integration;
- username/password authentication;
- MFA/SSO;
- organizations/teams;
- delegated access;
- user-management UI;
- distributed sessions;
- automatic retirement of the M37 operator compatibility path;
- frontend login/session UX.

These remain separate design/implementation decisions.

## Completion decision

M39 is complete for its accepted MVP scope. The next milestone must begin with a new design gate rather than expanding M39 opportunistically.
