# DEC-074 — M15 Market Opportunity Ranking Design Gate

**Status:** Proposed  
**Date:** 2026-09-18  
**Milestone:** M15 — Market Opportunity Ranking

## Context

M14 established market-wide execution: the system can execute an explicit ordered universe through the existing single-stock analysis capability and preserve per-stock results despite partial failures.

The next capability should turn completed per-stock opportunities into a deterministic, explainable market-wide view without changing the underlying stock-analysis rules.

## Problem

M14 intentionally does not rank opportunities, compare opportunities across stocks, filter by classification, define tie-breaking, or expose a market-wide opportunity view.

Without an explicit boundary, these responsibilities could leak into the dashboard, API, scheduler, or single-stock analysis pipeline.

## Desired Outcome

M15 should establish a dedicated application capability that:

1. consumes completed per-stock analytical results;
2. preserves existing stock-level scores and classifications;
3. derives deterministic market-wide ordering;
4. makes ordering explainable from existing analytical fields;
5. distinguishes eligible opportunities from non-opportunities;
6. handles missing or failed results explicitly;
7. remains independent of HTTP, React, providers, notifications, and trading execution.

## In Scope

- ranking input contract;
- ranking ownership;
- eligible classification policy;
- ranking key and comparison semantics;
- deterministic tie-breaking;
- empty input behavior;
- duplicate stock handling;
- missing-result handling;
- relationship to M14 execution outcomes;
- testability and determinism.

## Out of Scope

- changing Technical/Fundamental/Stock Quality/Entry Quality scoring;
- changing Opportunity Classification rules;
- portfolio allocation;
- position sizing;
- capital constraints;
- automated trading;
- notification delivery;
- dashboard UI;
- API endpoint design;
- historical ranking persistence;
- AI-based ranking;
- personalized ranking;
- price targets or stop-loss generation.

## Candidate Boundary

Market Analysis → Completed StockAnalysisResult set → Market Opportunity Ranking → Ordered Opportunity Set

The ranking capability should be an application-level composition over existing domain outputs. It must not recalculate analytical evidence.

## Alternatives Considered

### A. Add ranking to RunMarketAnalysis

Convenient access to results, but mixes execution orchestration with cross-stock comparison.

### B. Add ranking to the dashboard

Easy to display, but moves business ordering into presentation and prevents reuse by reports, automation, or future APIs.

### C. Add ranking to a dedicated application capability

Candidate: RankMarketOpportunities. This introduces an explicit application boundary while keeping market execution and market comparison independently testable.

### D. Make ranking part of OpportunityClassification

Would make a stock-level domain classification depend on other stocks, violating the existing stock-local analytical boundary.

## Open Questions

1. Which opportunity classifications are rankable?
2. What is the primary ranking measure?
3. Should Stock Quality and Entry Quality be separate ranking dimensions or supporting evidence only?
4. How should technical/fundamental status affect eligibility?
5. How should equal primary scores be ordered?
6. What is the deterministic final tie-breaker?
7. Should failed M14 symbols be absent from ranking or represented explicitly?
8. Should ranking consume raw StockAnalysisResult objects or a narrower ranking input model?
9. Should ranking return only eligible opportunities or a complete ordered market view?
10. Does M15 need a market-run identifier, or can it remain a pure function over supplied results?

## Design Constraints

1. Stock-level analytical rules remain unchanged.
2. Ranking is deterministic for the same inputs.
3. Ranking is explainable from existing stored fields.
4. Ranking does not introduce provider dependencies.
5. Ranking does not write persistence in the MVP.
6. Ranking does not make trading or portfolio decisions.
7. Missing or failed results must not silently become fabricated results.
8. API/dashboard integration requires a separate presentation design decision unless explicitly added to this gate.

## TDD Acceptance Shape

- empty ranking input;
- one eligible opportunity;
- multiple eligible opportunities;
- deterministic ordering;
- tie-breaking;
- non-eligible classifications;
- missing results;
- duplicate symbols;
- preservation of original analytical values;
- explainable ranking output;
- no mutation of source analysis results.

## Design Gate Decision

**Status: Proposed — implementation is not authorized by this document yet.**

The next action is to resolve the open questions and record the accepted ranking contract before writing M15 production code.

## Revisit Conditions

Revisit this design if the stock-level scoring model changes materially, opportunity classification gains new states, ranking becomes portfolio-aware, users require personalized ranking, historical ranking becomes persisted, or ranking requires real-time/distributed execution.
