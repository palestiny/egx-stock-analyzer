# DEC-075 — M16 Market Opportunity View Design Gate

**Status:** Accepted  
**Date:** 2026-09-18  
**Milestone:** M16 — Market Opportunity View

## Context

M15 established deterministic market-wide ranking as a pure application composition over completed `StockAnalysisResult` values.

The current API/dashboard slice remains single-stock oriented. The next user-facing capability is to expose the existing market opportunity ranking without moving ranking rules into HTTP or React.

## Problem

M15 can rank supplied results, but it does not define how stored analysis results become a reusable market-wide read model.

Without an explicit boundary, the API or dashboard could begin reading the persistence layer directly, reconstructing ranking inputs, or duplicating ranking rules.

## Desired Outcome

M16 establishes a read-side application capability and presentation contract that:

1. obtains completed stored analysis results for a requested universe;
2. reuses `RankMarketOpportunities` without recalculation;
3. distinguishes missing results from completed analytical results;
4. exposes a stable HTTP read contract;
5. lets the dashboard render the ordered opportunity set;
6. keeps persistence, ranking, and transport responsibilities separate.

## In Scope

- stored-result collection for a requested symbol universe;
- missing-result semantics;
- reuse of M15 ranking;
- read-side application boundary;
- HTTP endpoint contract;
- dashboard market-opportunity view;
- deterministic response ordering;
- tests for application, API, and presentation contracts.

## Out of Scope

- new analytical scoring;
- changes to OpportunityClassification;
- changing M15 ranking keys;
- historical ranking;
- watchlist persistence;
- personalized ranking;
- portfolio allocation;
- position sizing;
- automated trading;
- notification delivery;
- real-time streaming;
- concurrent market execution;
- AI ranking.

## Accepted Decisions

### 1. Read-Side Capability

Introduce a dedicated application capability:

`GetMarketOpportunityRanking`

It owns collection of stored completed results and delegates ordering to `RankMarketOpportunities`.

It must not execute fresh stock analysis.

This keeps the distinction explicit:

```
RunMarketAnalysis
    = execute analysis

GetMarketOpportunityRanking
    = read stored results + rank

RankMarketOpportunities
    = pure cross-stock ordering
```

### 2. Universe Input

The MVP accepts an explicit ordered list of symbols from the caller.

A separate persistent watchlist/universe-management feature is deferred.

The application normalizes symbols and rejects duplicate normalized symbols before reading results.

### 3. Missing Results

Missing stored results are omitted from the ranking input and returned as explicit metadata in the read model.

They are not treated as zero scores and are never passed to the ranking capability as synthetic results.

This preserves the M15 rule that missing results are not fabricated.

### 4. Result Date Semantics

The read capability uses the latest stored result available for each requested symbol.

The existing `AnalysisResultStore` contract remains the source of truth; M16 does not introduce history or date-selection semantics.

### 5. API Contract

Add a read-only endpoint:

`GET /api/v1/opportunities?symbols=EGAL,IEEC,COMI`

The response contains:

- ordered opportunities;
- requested symbols;
- missing symbols.

The API returns ranking data already computed by the application layer and does not calculate scores.

An empty symbol list returns an empty opportunity view rather than triggering market execution.

### 6. Dashboard Boundary

The dashboard consumes the new HTTP read model and renders:

- ranked opportunity rows;
- symbol;
- classification;
- stock quality;
- entry quality;
- technical score;
- fundamental score;
- missing-result state.

The dashboard does not rank, filter by classification, calculate scores, or access persistence directly.

### 7. Freshness / Execution

The endpoint is read-only and does not trigger analysis.

Fresh analysis remains an explicit execution concern owned by M14 and future scheduling/automation capabilities.

### 8. Persistence

No new persistence schema is introduced.

M16 reads through `AnalysisResultStore` only.

### 9. Determinism

The response preserves the deterministic M15 ranking order. Missing symbols retain deterministic metadata ordering based on the normalized caller input.

## Application Boundary

```
HTTP
  ↓
GetMarketOpportunityRanking
  ↓
AnalysisResultStore
  ↓
RankMarketOpportunities
  ↓
Ordered Opportunity Read Model
  ↓
HTTP / Dashboard
```

The ranking capability remains independent from FastAPI and React.

## TDD Acceptance Criteria

### Application

- empty universe returns empty opportunities and no missing symbols;
- all stored results are ranked through M15;
- missing results are reported explicitly and excluded from ranking;
- duplicate normalized symbols are rejected;
- source results are preserved;
- no analysis execution occurs;
- M15 ranking order is preserved.

### API

- endpoint accepts a symbol list;
- response contains ordered opportunities;
- response contains missing symbols;
- empty input is valid;
- duplicate normalized symbols return a validation error;
- no stored result does not produce a server error;
- endpoint does not execute fresh analysis.

### Dashboard

- renders ranked opportunities from API data;
- renders missing-result state;
- preserves API order;
- has loading, empty, and transport-error states;
- contains no ranking or analytical calculation logic.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M16 MVP defined here.**

M16 is a presentation/read-side extension of the existing analytical system. It does not change the analytical brain, M14 execution semantics, or M15 ranking contract.

## Revisit Conditions

Revisit this design if the product requires persistent watchlists, historical rankings, personalized ranking, live streaming, portfolio-aware ranking, or analysis-on-demand from the market opportunity endpoint.
