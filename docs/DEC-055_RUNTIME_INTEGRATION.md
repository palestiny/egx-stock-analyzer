# DEC-055 — Runtime Integration for M12 Dashboard

**Status:** Accepted
**Date:** 2026-09-16
**Scope:** M12 API + Dashboard runtime integration

## Context

The M12 dashboard already has a tested API client and analysis screen, while the backend API requires an application-level `AnalysisResultStore`.

The remaining integration concern is how the application is composed and how the browser reaches the backend during local development.

## Decision

1. The backend composition root is `app/main.py`.
2. `app/main.py` creates the `InMemoryAnalysisResultStore`, passes it to `create_app(...)`, and exports the resulting ASGI application as `app`.
3. `uvicorn` is an explicit project dependency so the backend can be started with:

   ```text
   uvicorn app.main:app --reload
   ```

4. `httpx` is an explicit dependency because FastAPI's `TestClient` uses it for runtime API tests.
5. Vite proxies `/api` requests to `http://127.0.0.1:8000` during local development.
6. The browser continues to call `/api/v1/analysis/{symbol}` and does not need CORS configuration for this local setup.
7. The composition root contains wiring only; it does not contain analysis or business rules.
8. The runtime does not seed fake analysis results merely to make the dashboard display data. Real analysis results will be supplied by the existing analysis pipeline when that integration is completed.

## Alternatives Considered

### CORS Instead of a Vite Proxy

Rejected for the MVP because it adds cross-origin configuration when the dashboard and backend can appear under one browser origin through the development proxy.

### Fake API Endpoint for Dashboard Demonstration

Rejected because it would create a second path that bypasses the real analysis pipeline and could hide integration problems.

### Dependency Injection Framework at Startup

Rejected for the MVP because the composition root only needs a small amount of explicit wiring.

## Trade-offs

### Gains

- explicit application composition
- clean API/domain boundary
- simple local development setup
- no CORS configuration for the dashboard/backend development flow
- reproducible API integration tests
- clean-environment ASGI startup

### Costs

- one composition-root module
- explicit `uvicorn` and `httpx` dependencies
- Vite development proxy configuration

## Consequences

The backend can now be treated as a real ASGI application rather than only a factory function.

The dashboard can use the same `/api` URL shape in the browser regardless of whether the backend is reached through the Vite development proxy or another deployment boundary later.

The in-memory result store remains intentionally temporary. Persistence, history, multi-process behavior, and production deployment configuration remain separate decisions.

## Verification

The composition root is covered by an API test asserting that a missing analysis result returns HTTP 404 with the established API contract.
