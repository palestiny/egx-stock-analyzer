# DEC-074 — Market-Wide Opportunity Ranking Design Gate

**Status:** Proposed  
**Date:** 2026-09-18  
**Milestone:** M15

## Context

M14 established deterministic market-wide execution. A requested universe can now be analyzed sequentially through the existing single-stock capability, while successful per-stock results remain available through AnalysisResultStore.

The project goal is not only to analyze every stock. It also needs to help identify which analyzed opportunities deserve attention.

The current StockAnalysisResult already contains technical score, fundamental score, stock quality score, entry quality score, opportunity classification, technical/fundamental evidence, and entry context.

## Problem

The system currently produces independent stock results but has no explicit application capability for answering:

> Given a completed set of stock analysis results, in what deterministic order should opportunities be presented?

This is different from calculating a stock's score, deciding BUY/WATCH/HOLD/AVOID, selecting the universe, running market analysis, allocating a portfolio, or executing trades.

## Desired Outcome

Introduce a market-wide ranking capability that:

1. consumes completed analysis results;
2. ranks only according to explicitly accepted ranking rules;
3. does not recalculate technical, fundamental, stock-quality, or entry-quality scores;
4. keeps classification separate from ordering;
5. makes missing/failed analysis explicit;
6. produces deterministic output;
7. is reusable by reports, API, dashboard, and future automation.

## Scope

### In scope
- ranking input contract;
- eligibility rules;
- ordering semantics;
- tie-breaking;
- deterministic behavior;
- handling missing results;
- relationship to existing scores/classification;
- application/domain ownership;
- testability.

### Explicitly out of scope
- changing existing score formulas;
- changing BUY/WATCH/HOLD/AVOID rules;
- portfolio allocation;
- position sizing;
- stop-loss or target calculation;
- watchlists;
- notifications;
- trading execution;
- AI ranking;
- personalized investor preferences;
- provider behavior;
- database schema changes.

## Current Architectural Boundary

The intended direction is:

Market-Wide Analysis
        ↓
AnalysisResultStore
        ↓
Opportunity Ranking
        ↓
Report / API / Dashboard

Ranking should consume existing analytical results rather than invoke market-data providers or rerun analysis.

## Alternatives Considered

### A — Sort directly in the dashboard/API

Small initial implementation, but transport/presentation becomes responsible for business ordering, behavior gets duplicated across clients, and scheduled reports cannot reuse the same capability cleanly.

**Assessment:** Not selected.

### B — Add ranking to RunMarketAnalysis

Convenient because results are produced there, but it couples execution and ordering, prevents ranking previously persisted results cleanly, and gives one component two distinct responsibilities.

**Assessment:** Not selected.

### C — Dedicated ranking application capability

Conceptually:

GetMarketOpportunityRanking
        ↓
AnalysisResultStore
        ↓
existing StockAnalysisResult

Trade-offs: explicit responsibility, reusable by API/report/dashboard/automation, testable without providers, with one additional application capability.

**Assessment:** Preferred candidate.

## Open Questions

These must be resolved before implementation:

1. Eligibility: should ranking include every successfully analyzed stock, or only BUY/WATCH candidates?
2. Primary ordering: should the first MVP order by stock quality, entry quality, or an explicit composite ranking score?
3. Classification: should BUY/WATCH/HOLD/AVOID affect ordering, merely filter eligibility, or remain informational?
4. Tie-breaking: what deterministic secondary and tertiary keys should resolve equal scores?
5. Failed/missing results: should they be excluded from ranked output and exposed separately?
6. Analysis date: must all ranked results belong to one analysis date?
7. Snapshot consistency: should ranking read current stored results only, or require a market-wide execution identity?
8. Top-N: should the use case return the complete ranking and let consumers truncate it, or own a limit?
9. Future strategy changes: how should ranking rules be versioned if the project later changes the scoring model?
10. Domain vs application ownership: is ranking itself a domain rule, or is it an application projection over existing domain results?

## Proposed Invariants

1. Ranking never recalculates analytical scores.
2. Ranking never changes opportunity classification.
3. Ranking never invokes external providers.
4. Equal inputs produce equal ordering.
5. Tie-breaking is explicit and deterministic.
6. Missing/failed analysis is never silently represented as a valid ranked opportunity.
7. Consumers do not implement their own ranking rules.
8. Ranking can operate on persisted results without rerunning analysis.

## TDD Acceptance Shape

Before implementation, tests should establish at least:
- ranking multiple completed results;
- deterministic ordering;
- equal-score tie behavior;
- classification/eligibility behavior;
- missing result handling;
- failed analysis handling;
- analysis-date consistency;
- complete ranking vs top-N behavior;
- no recalculation/provider dependency;
- empty input.

## Design Gate Rule

No implementation should begin until the ranking semantics are explicitly accepted.

The key architectural goal is to prevent M15 from quietly turning an existing scoring model into a new, undocumented scoring model.

## Revisit Conditions

Revisit this gate if:
- portfolio construction becomes the primary consumer;
- investor-specific preferences become required;
- historical ranking comparison becomes required;
- scoring formulas change materially;
- real-time ranking becomes an operational requirement;
- ranking needs external data not already present in StockAnalysisResult.