# DEC-067 — M12 Frontend Technology

**Status:** Accepted  
**Date:** 2026-09-18

## Context

M12 requires a small dashboard presentation client for the existing HTTP API. The repository currently has no frontend application.

The project owner has existing React/JavaScript experience, and the first dashboard slice needs component-based UI composition without introducing backend business logic into the client.

## Decision

Use **React with Vite** for the M12 dashboard.

The frontend will live under:

```text
frontend/
```

It will be a presentation client only.

The frontend will communicate with the existing FastAPI HTTP API and will not import Python/domain code.

## Why

React provides:

- component-based composition for the dashboard
- a direct fit with the project's existing React/JavaScript skill set
- a small initial implementation surface
- a straightforward path to later dashboard screens without committing to a larger frontend architecture

Vite provides the development/build tooling without introducing a full-stack framework at this stage.

## Alternatives Considered

### Server-rendered HTML

Would minimize frontend dependencies, but provides less reuse and component structure for the dashboard as it grows.

### Lightweight static JavaScript

Would minimize tooling, but would create more manual UI composition as the dashboard expands.

### React + Vite

Selected because it provides the required component model while keeping the frontend boundary simple.

## Boundaries

The frontend may:

- fetch API DTOs
- manage loading/error/empty UI state
- format values for display
- compose reusable presentation components
- navigate between presentation views

The frontend must not:

- calculate scores
- classify opportunities
- calculate support/resistance
- access Yahoo Finance
- implement alert-generation rules
- persist analytical state as a second source of truth
- execute trades

## Consequences

A frontend build/runtime is now part of M12.

The backend API remains the source of analytical meaning.

If the frontend technology changes later, the API/domain boundaries should remain unchanged.

## Revisit Conditions

Reconsider this decision only if actual requirements demonstrate a need that React/Vite cannot satisfy reasonably, or if the project deliberately changes its frontend strategy.
