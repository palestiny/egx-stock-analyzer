# DEC-066 — M12 Dashboard / Presentation Boundary

**Status:** Accepted  
**Date:** 2026-09-17

## 1. Design Question

How should a dashboard consume the existing M12 analysis, report, and alert capabilities without moving business rules into the presentation layer?

## 2. Current Evidence

The backend already exposes read-side projections:

- `GET /api/v1/analysis/{symbol}`
- `GET /api/v1/reports/{symbol}`
- `GET /api/v1/alerts/{symbol}`

The focused report/alert contract suite is locally green:

```text
17 passed, 2 warnings
```

No frontend application currently exists in the repository.

## 3. Proposed Decision

The dashboard will be a **presentation client** of the existing HTTP API.

The dashboard may:

- select/display a stock symbol
- request analysis/report/alert data
- present scores and statuses
- display support/resistance and current price
- display the opportunity classification returned by the API
- show loading, empty, unavailable, and transport-error states
- format values for human presentation
- provide navigation and presentation-level filtering

The dashboard must not:

- calculate technical or fundamental scores
- calculate Stock Quality or Entry Quality
- classify BUY/WATCH/HOLD/AVOID
- calculate support/resistance
- create alert candidates
- decide BUY thresholds
- fetch Yahoo Finance directly
- contain provider-specific logic
- persist analytical results as a second source of truth
- implement notification delivery
- introduce trading execution

The conceptual boundary is:

```text
Dashboard
   ↓ HTTP
API
   ↓
Application Capabilities
   ↓
Domain
   ↓
Infrastructure
```

The dashboard is therefore a consumer, not an owner, of analytical meaning.

## 4. MVP Dashboard Surface

The first dashboard slice should remain deliberately small.

### Stock Analysis View

Input:

- stock symbol

Display:

- symbol
- analysis date
- current price when available
- technical score
- fundamental score
- stock quality score
- entry quality score
- opportunity classification
- nearest support when available
- nearest resistance when available
- trend
- momentum
- volume
- profitability
- liquidity
- growth

### Alert Indicator

The dashboard may show that an alert candidate exists for the selected stock.

It must not generate the candidate itself.

### Explicitly Deferred

- market-wide ranking
- watchlists
- portfolio management
- interactive technical charting
- historical comparison
- notification configuration
- user accounts
- authentication/authorization
- automated trading
- dashboard-side analytics
- real-time streaming
- advanced filtering
- mobile-specific application

These require separate design decisions when their actual requirements emerge.

## 5. API Contract Boundary

The dashboard should consume transport DTOs rather than domain objects.

Current report DTO:

```text
symbol
analysis_date
fundamental_period_end
technical_score
fundamental_score
stock_quality
entry_quality
opportunity
current_price
nearest_support
nearest_resistance
trend
momentum
volume
profitability
liquidity
growth
```

Current alert DTO:

```text
stock_id
classification
stock_quality_score
entry_quality_score
```

The dashboard must treat these as API representations.

It must not infer missing business semantics from presentation values.

## 6. Decimal Transport

The API currently serializes Decimal values as JSON strings, for example:

```json
{
  "current_price": "350.5",
  "nearest_support": "340.0",
  "nearest_resistance": "365.0"
}
```

The dashboard should preserve the received decimal value for display and must not silently introduce floating-point calculations for business decisions.

If future UI requirements need numeric charting, that is a separate API-contract decision rather than an implicit frontend conversion.

## 7. Error / Empty-State Semantics

The dashboard should distinguish at least:

- loading
- successful result
- no report / 404
- no alert candidate / 404
- API unavailable / transport failure

A 404 from the alert endpoint means there is no alert candidate for the latest stored result; it must not be interpreted by the UI as an API failure.

The dashboard must not invent fallback analytical classifications.

## 8. Technology Boundary

No frontend framework is committed by this proposal.

Candidate implementations include:

1. React-based client.
2. Server-rendered HTML.
3. Lightweight static client.

The implementation choice should be made based on the actual dashboard requirements and project learning objective, not because a framework is fashionable.

If React is selected, it remains a presentation technology and must not alter the backend domain/application boundaries.

## 9. Alternatives Considered

### A. Put dashboard logic in FastAPI

Rejected for the MVP boundary.

Reason:

It would encourage presentation concerns and analytical rules to become mixed in the API layer.

### B. Let the dashboard calculate scores/classification

Rejected.

Reason:

This creates a second implementation of business rules and makes API/domain results non-authoritative.

### C. Build a large dashboard before validating the first screen

Rejected for the MVP.

Reason:

It would introduce UI complexity before the API consumption boundary is validated.

### D. Small API-driven dashboard slice

Proposed.

Reason:

It validates the end-to-end presentation boundary with minimal new behavior.

## 10. Trade-offs

### Gains

- Clear ownership of analytical rules.
- Thin presentation layer.
- Easy replacement of frontend technology.
- Reusable API for future clients.
- Small implementation surface.
- Strong alignment with domain-first architecture.

### Costs

- Some presentation needs may require future API DTO changes.
- The dashboard cannot independently calculate business-derived values.
- Additional HTTP boundary and frontend testing are required.

## 11. Open Questions

These are intentionally not implementation blockers yet:

- Which frontend technology should be selected?
- Should the first dashboard use one stock-analysis screen only?
- Do we need a dedicated API endpoint for stock search/catalog?
- Should the report endpoint eventually expose a symbol-based alert identity rather than only UUID?
- What charting requirements, if any, justify additional API data?

## 12. Committed vs Proposed

The dashboard presentation boundary is accepted by DEC-067. The frontend technology is React + Vite.

The following boundary is committed:

> **Dashboard displays analytical results; backend owns analytical meaning.**

The following remain open:

- exact first-screen UX refinements
- additional API endpoints needed by the dashboard

Implementation may proceed under the accepted React + Vite decision. Remaining open questions are scope refinements, not blockers for the first vertical slice.

## 13. Acceptance Criteria for the Gate

The dashboard boundary is ready for implementation when:

- presentation responsibilities are separated from business responsibilities
- the first screen's required data is identified
- the API DTOs are sufficient or explicit API changes are identified
- error/empty-state semantics are defined
- frontend technology is selected
- the first dashboard slice has tests or an agreed UI validation strategy

