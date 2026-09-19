# DEC-100 — M40 Frontend Authentication & Session UX Design Gate

**Status:** Accepted  
**Date:** 2026-09-19  
**Milestone:** M40 — Frontend Authentication & Session UX

## Context

M39 established multi-user bearer authentication at the HTTP/application boundary and intentionally deferred frontend login/session UX. The React dashboard currently has no user-facing authentication flow.

## Decision

M40 adds a minimal frontend authentication boundary that uses the existing M39 bearer credential mechanism.

The browser does not implement password authentication, user provisioning, token issuance, refresh tokens, or identity-provider flows.

### Accepted UX

- Show a login screen when no frontend credential is present.
- Accept a bearer credential through a password-style input.
- Store the credential in sessionStorage, not localStorage.
- Send it only through the HTTP Authorization: Bearer <token> header.
- Validate the credential by calling a protected identity endpoint.
- On successful validation, render the existing dashboard.
- Provide an explicit logout action that clears the session credential.
- HTTP 401 clears the frontend session and returns the user to login.
- HTTP 403 remains an authorization error and does not silently log the user out.
- Health remains public and is not used as authentication validation.

### Identity endpoint

Add GET /api/v1/auth/me.

It returns the authenticated application identity needed by the frontend session:

- immutable user ID;
- authentication/identity status suitable for presentation.

The endpoint does not return credentials, tokens, secrets, or ownership data.

### Boundary

```
Login UI
  ↓
Frontend Session
  ↓
API Client Authorization Header
  ↓
GET /api/v1/auth/me
  ↓
AuthenticatedIdentity
  ↓
Existing Protected APIs
```

The frontend owns presentation/session state only. Authentication remains backend-owned.

## Security Constraints

- No token in URL, query string, React markup, or API payload.
- No token persistence in localStorage.
- No automatic token refresh.
- No password storage.
- Logout clears the browser session credential.
- Existing backend 401/403 semantics remain authoritative.
- The frontend must not infer identity from a client-supplied user ID.

## Explicitly Out of Scope

- signup;
- password authentication;
- password reset;
- MFA;
- SSO;
- external IdP integration;
- refresh-token rotation;
- persistent browser sessions;
- role/permission administration;
- organization/team UX;
- user profile management.

## TDD Acceptance Criteria

- no stored credential renders login;
- valid credential authenticates through GET /api/v1/auth/me;
- invalid credential returns to login;
- authenticated dashboard requests include the bearer header;
- 401 clears the session and returns to login;
- 403 remains an authorization error;
- logout clears the session;
- token is never sent in URL/query/body;
- session survives React reload within the same browser tab;
- closing the tab removes the session because sessionStorage is used;
- GET /api/v1/auth/me never returns raw credentials.

## Revisit Conditions

Revisit when persistent login, refresh tokens, external identity providers, MFA, password authentication, or richer user-profile requirements become product requirements.
