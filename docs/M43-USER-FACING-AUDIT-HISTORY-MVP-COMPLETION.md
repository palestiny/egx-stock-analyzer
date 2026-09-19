# M43 — User-Facing Audit History MVP Completion

**Status:** Complete  
**Date:** 2026-09-19  
**Design:** `docs/DEC-104-M43-USER-FACING-AUDIT-HISTORY-DESIGN-GATE.md`  
**Implementation PR:** #96

## Delivered

M43 adds a read-only personal audit-history capability over the durable M41 management-audit boundary.

### Application

- Added `GetUserAuditHistory`.
- Visibility is target-only and always scoped to the authenticated immutable user ID.
- M41 user-account actions are explicitly allowlisted.
- Unknown future actions are excluded by default.
- Actor identity is redacted to relative labels: `self` or `operator`.
- Target identity is represented as `self`.
- No raw actor/target UUIDs are exposed.
- Safe action/outcome filters are supported.
- Pagination remains bounded to 50 default / 100 maximum.
- Existing deterministic audit ordering is reused.
- M42 operator audit reporting remains unchanged.

### API

Added:

`GET /api/v1/users/me/audit`

The endpoint requires normal authentication but does not require operator permission.

### Dashboard

Added a read-only **My security history** panel for authenticated users with:

- action filter;
- outcome filter;
- loading state;
- empty state;
- error state;
- bounded previous/next pagination;
- relative actor labels.

The dashboard does not implement authorization or redaction rules.

### Persistence

The existing management-audit store was extended with an application-controlled action allowlist query. No new audit table or history source of truth was introduced.

### Tests

Added focused application/API/frontend tests for:

- target isolation;
- actor/target redaction;
- allowlisted actions;
- pagination validation;
- authentication boundary;
- dashboard rendering;
- dashboard empty state;
- regression compatibility with existing dashboard tests.

## Verification

GitHub Actions Run #1599 passed:

- Python unit tests: success;
- frontend tests: success;
- frontend production build: success.

## Explicit non-goals

M43 does not add:

- actor-or-target visibility;
- cross-user audit access;
- new roles or permissions;
- organizations/delegated administration;
- retention changes;
- real-time audit streaming;
- SIEM integration;
- audit analytics;
- audit-write changes;
- credential or lifecycle changes.

## Completion Boundary

```
Authenticated User
        ↓
GET /api/v1/users/me/audit
        ↓
GetUserAuditHistory
        ↓
ManagementAuditStore
        ↓
SQLite
```

M43 is complete when the user-facing read boundary is available without weakening the existing M41/M42 audit semantics.
