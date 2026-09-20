# M40 — User Authentication & Credential Lifecycle MVP Completion

**Status:** Complete  
**Date:** 2026-09-19  
**Design:** DEC-100 + DEC-101

## Completed Boundary

M40 now provides:

- browser login/session UX over the existing bearer transport;
- durable application-managed opaque bearer credentials;
- one-way credential verification at rest;
- credential provisioning through the application security service;
- credential rotation with atomic durable replacement;
- credential revocation;
- disabled/deleted user rejection during authentication;
- M39 configured-credential compatibility;
- preservation of immutable AuthenticatedIdentity;
- preservation of the M38 ownership authorization boundary.

## Persistence

Credential lifecycle state is stored in the existing SQLite deployment through the dedicated CredentialStore boundary.

Raw credential values are never persisted or returned after the one-time provisioning/rotation result.

## Frontend Boundary

The existing M40 frontend session behavior remains:

- credential accepted at login;
- stored only in browser sessionStorage for the browser session;
- validated through GET /api/v1/auth/me;
- cleared on explicit logout or HTTP 401;
- HTTP 403 remains an authorization response and does not silently log the user out.

No password system, MFA/SSO, commercial identity provider, or second server-side session store was introduced.

## Validation

Implementation PR #88 was merged after GitHub Actions Run #1420 completed successfully.

Validated jobs:

- Python unit tests: success
- Frontend tests: success
- Frontend production build: success

The focused M40 tests cover provisioning, authentication, invalid credentials, revocation, rotation, disabled users, persistence/reload, M39 compatibility, credential ownership, and raw-secret non-persistence.

## Deferred

- password authentication;
- password reset/recovery;
- MFA/SSO;
- external identity-provider integration;
- automatic credential expiration;
- self-service registration;
- user-management UI;
- organizations/teams;
- delegated access;
- distributed session storage.

These remain separate future design decisions.
