# DEC-074 — M15 Market Opportunity Ranking Design Gate

**Status:** Accepted  
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

## Accepted Decisions

### 1. Rankable Classifications

M15 ranks only BUY and WATCH results. HOLD and AVOID remain part of supplied analytical results but are not included in the opportunity set.

This keeps the ranking focused on attention states already defined by the stock-level classifier rather than inventing a second classification system.

### 2. Primary Ranking Measure

The primary ranking measure is StockQualityScore.total_score.

No new aggregate opportunity score is introduced in M15. The existing stock-quality score is already an explicit composite of technical and fundamental scores.

### 3. Secondary Ranking Measure

EntryQualityScore.total_score is the second ranking dimension.

This preserves the project's distinction between stock quality and entry quality instead of collapsing them into a new opaque number.

### 4. Additional Tie-Breaking Evidence

If stock quality and entry quality are equal, use:

1. technical score descending;
2. fundamental score descending;
3. symbol ascending.

The final symbol ordering makes the result deterministic even when all numerical values are equal.

### 5. Technical/Fundamental Status

M15 does not add a separate eligibility rule based on technical/fundamental status fields. Existing OpportunityClassification remains the source of eligibility.

### 6. Failed and Missing Results

Failed M14 executions and missing analytical results are excluded from the ranked opportunity set. They are not converted into zero scores or synthetic results.

The ranking input contract therefore receives only completed StockAnalysisResult records. Callers that need failure reporting continue to use M14 execution outcomes.

### 7. Ranking Input Model

The ranking capability accepts a narrow immutable input containing the stock symbol and its StockAnalysisResult, rather than depending on the full market execution object.

### 8. Output Shape

M15 returns an immutable ordered opportunity collection containing symbol plus the original StockAnalysisResult. The source analytical result is not mutated or recalculated.

### 9. Market Run Identity

M15 remains a pure composition over supplied results. It does not require a market-run identifier and does not persist rankings.

### 10. Duplicate Symbols

Duplicate normalized symbols are rejected before ranking because they make the output ambiguous.

## Design Gate Decision

**Status: Accepted — implementation is authorized for the M15 MVP defined here.**

Application boundary:

Market Analysis → Completed Results → RankMarketOpportunities → Ordered Opportunity Set

The ranking capability owns only cross-stock ordering and eligibility selection. It does not own analysis, scoring, persistence, API transport, dashboard rendering, notifications, or trading decisions.

## TDD Acceptance Criteria

- empty input returns an empty immutable opportunity set;
- BUY and WATCH results are included;
- HOLD and AVOID results are excluded;
- stock quality orders opportunities first;
- entry quality breaks stock-quality ties;
- technical score breaks the next tie;
- fundamental score breaks the next tie;
- symbol ascending is the final deterministic tie-breaker;
- duplicate normalized symbols are rejected;
- source StockAnalysisResult objects are preserved without mutation;
- ranking performs no analytical recalculation;
- missing/failed results are represented by omission from the ranking input rather than synthetic scores.
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

**Status: Accepted — implementation is authorized for the M15 MVP defined here.**

Application boundary:

Market Analysis → Completed Results → RankMarketOpportunities → Ordered Opportunity Set

The ranking capability owns only cross-stock ordering and eligibility selection. It does not own analysis, scoring, persistence, API transport, dashboard rendering, notifications, or trading decisions.

## Revisit Conditions

Revisit this design if the stock-level scoring model changes materially, opportunity classification gains new states, ranking becomes portfolio-aware, users require personalized ranking, historical ranking becomes persisted, or ranking requires real-time/distributed execution.
