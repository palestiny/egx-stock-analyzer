# M16 — Market Opportunity View Completion

**Status:** Complete  
**Date:** 2026-09-18  
**Design Gate:** DEC-075  
**Implementation PR:** #12

## Delivered

M16 adds a read-side market opportunity capability without changing stock-level analysis or M15 ranking rules.

### Application

- Added `GetMarketOpportunityRanking`.
- Reads latest stored results through `AnalysisResultStore`.
- Normalizes and validates requested symbols.
- Reports missing symbols explicitly.
- Reuses `RankMarketOpportunities`.
- Does not execute fresh analysis.
- Does not introduce persistence changes.

### API

Added:

```
GET /api/v1/opportunities?symbols=EGAL,IEEC,COMI
```

The response exposes the ordered opportunity set, requested symbols, and missing symbols.

### Dashboard

Added a market opportunity view that:

- renders ranked opportunity rows;
- preserves API ordering;
- shows classification and score fields;
- reports missing stored results;
- handles loading, empty, and transport-error states;
- contains no ranking or analytical calculations.

## Validation

GitHub Actions Run #281 completed successfully for implementation head:

`ac3d0dff1348952c55e129dc03d8fcc4962579ea`

The implementation was merged through PR #12.

## Deferred

M16 does not add:

- watchlist persistence;
- historical ranking;
- personalized ranking;
- portfolio allocation;
- position sizing;
- automated trading;
- real-time streaming;
- analysis-on-demand from the opportunity endpoint;
- AI ranking.

These remain candidates for future design gates.
