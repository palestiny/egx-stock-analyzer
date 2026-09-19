# M41 — User Management & Credential Administration MVP Completion

**Milestone:** M41  
**Design:** DEC-102  
**Status:** Complete  
**Implementation PR:** #90  
**Merged:** 2026-09-19

## Delivered

M41 establishes the first controlled user-management capability over the existing M38/M39/M40 identity, ownership, and credential boundaries.

### Application

- operator user listing;
- operator user creation;
- one-time credential issuance;
- ACTIVE / DISABLED / DELETED lifecycle transitions;
- bootstrap legacy operator protection;
- operator rotation of durable credentials;
- self-service rotation of the authenticated durable credential;
- explicit rejection of self-service rotation for M39 configured-only credentials;
- minimal durable management audit events.

### API

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}/status`
- `POST /api/v1/users/{user_id}/credentials/rotate`
- `POST /api/v1/users/me/credentials/rotate`

Credential endpoints return the newly issued raw credential only as the immediate command result. Raw credentials are not stored or included in audit events.

### Dashboard

The existing authenticated React dashboard now includes:
- self-service credential rotation;
- operator-only user administration;
- user listing;
- create-user flow;
- disable/reactivate/delete controls;
- operator credential rotation.

The dashboard remains presentation-only and delegates all identity, lifecycle, authorization, and credential behavior to the API/application boundary.

## Persistence

A dedicated `management_audit` SQLite table persists security-sensitive management events. Existing user and credential stores remain separate application boundaries while sharing the current SQLite deployment.

## Validation

GitHub Actions Run #1488 passed for implementation head:

`63ff880c7b8d34d0551f76f73515ea3a0e6d0839`

Validated:
- Python unit tests — success
- Frontend tests — success
- Frontend production build — success

## Deferred

- public/self-service registration;
- profile fields;
- password authentication and recovery;
- MFA / SSO;
- external identity providers;
- richer role management;
- organizations and delegated access;
- audit query/reporting UI;
- automatic credential expiration;
- retirement of M39 configured-credential compatibility.

## Architectural Result

M41 keeps the boundary:

```
Authentication
    ↓
AuthenticatedIdentity
    ↓
Application Authorization
    ↓
UserManagementService
    ↓
UserStore / CredentialStore / ManagementAuditStore
```

Analytical domain modules remain identity-agnostic.
