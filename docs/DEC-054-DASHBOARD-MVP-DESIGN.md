# DEC-054 — Dashboard MVP Design

## Status
Accepted

## Context
M12 needs a first useful dashboard vertical slice on top of the completed analysis API. The dashboard must consume the stable HTTP contract rather than reproduce analysis or business rules in the browser.

## Goal
Provide a minimal read-only stock analysis screen that lets a user enter a symbol and inspect the completed analysis summary returned by:

`GET /api/v1/analysis/{symbol}`

## Decision

### Frontend stack
- React
- Vite
- JavaScript
- Plain CSS for the MVP

Tailwind CSS is intentionally deferred. The first slice should validate the application/API/UI boundary before introducing a styling framework.

### Frontend location
The frontend lives in a separate top-level directory:

`frontend/`

The existing Python application remains the backend/application/domain source of truth.

### MVP screen
The first screen contains:

1. Symbol input
2. Search / Analyze button
3. Loading state
4. API error state
5. Not-found state
6. Analysis summary cards for:
   - Technical Score
   - Fundamental Score
   - Stock Quality
   - Entry Quality
   - Opportunity

No charts, historical data, watchlist, authentication, editing, or analysis execution controls are included in this slice.

### API boundary
The browser calls only the existing API endpoint:

`GET /api/v1/analysis/{symbol}`

The frontend does not calculate scores, classify opportunities, interpret technical indicators, or duplicate domain rules.

### Client boundary
Create a small API client module responsible only for HTTP communication and response parsing. React components consume the client rather than constructing fetch details throughout the UI.

## Testing decision
Use Vitest and React Testing Library for frontend behavior tests.

The first tests will cover:

- rendering the symbol input and action
- successful result rendering
- loading state
- API failure state
- 404 / missing-result state

Tests will verify observable UI behavior, not implementation details.

## Design constraints
- Keep the dashboard read-only.
- Keep business logic in Python application/domain layers.
- Do not create dashboard-specific aggregation endpoints unless the MVP proves the existing API is insufficient.
- Do not introduce state-management libraries for this slice.
- Do not introduce routing until more than one meaningful screen exists.

## Vertical slice
The implementation sequence is:

`React shell → API client → analysis screen → tests → API integration → build verification`

The slice is complete only when the frontend tests and production build are green and the documented API contract remains unchanged.

## Deferred
- Tailwind CSS
- React Router
- global state management
- charts
- historical analysis
- watchlists
- authentication/authorization
- dashboard aggregation APIs
- live polling
- production deployment configuration
