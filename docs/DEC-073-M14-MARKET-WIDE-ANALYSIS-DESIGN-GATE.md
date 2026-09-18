# DEC-073 — Market-Wide Analysis Capability Design Gate

**Status:** Proposed  
**Date:** 2026-09-18  
**Milestone:** M14

## Context

The current system can execute analysis for an individual stock symbol and can persist the latest completed result per symbol.

The project's stated purpose, however, is broader than single-symbol analysis: the system should eventually analyze the EGX stock universe consistently and expose the resulting opportunities.

The current architecture already contains important building blocks:

```
StockCatalog
    ↓
RunStockAnalysisBySymbol
    ↓
RunStockAnalysis
    ↓
AnalysisInputAssembler
    ↓
DailyMarketAnalysis
    ↓
AnalysisResultStore
```

The next capability should extend the application around these existing boundaries rather than move market-wide orchestration into the domain or dashboard.

## Problem

There is currently no explicitly designed application capability whose responsibility is:

> Take a defined stock universe for a given analysis date, execute analysis across that universe, preserve per-stock success/failure semantics, and expose an aggregate execution result.

This creates an important design question before implementation:

- What exactly constitutes the analysis universe?
- Who owns selection and ordering?
- What happens when some stocks fail?
- What does a market-wide run mean when data is unavailable for one symbol?
- Should one failure stop the entire run?
- How should the aggregate run be represented?
- What relationship should exist between market-wide execution and the existing per-symbol use case?

## Desired Outcome

Introduce a market-wide analysis application capability that can:

1. obtain a defined stock universe;
2. execute the existing stock-analysis capability for each stock;
3. preserve the existing per-stock domain/application rules;
4. distinguish aggregate execution state from individual stock outcomes;
5. persist successful per-stock results through the existing `AnalysisResultStore` boundary;
6. make partial success and failure explicit;
7. remain independent from HTTP, dashboard, provider-specific APIs, and notification delivery.

## Scope of This Design Gate

This gate covers only the application-level market-wide execution boundary.

### In scope

- stock-universe input/selection contract;
- orchestration ownership;
- per-stock execution semantics;
- aggregate execution semantics;
- partial failure behavior;
- interaction with `RunStockAnalysis`;
- interaction with `AnalysisResultStore`;
- testability;
- deterministic execution behavior.

### Explicitly out of scope

- ranking opportunities;
- watchlists;
- historical result browsing;
- new persistence schema;
- notification delivery;
- authentication;
- dashboard changes;
- provider failover;
- distributed workers;
- concurrency/scaling;
- trading decisions;
- portfolio allocation;
- AI-based selection.

Those capabilities require separate design decisions.

## Current Architectural Boundary

The intended direction is:

```
Market-Wide Application Use Case
          ↓
Stock Universe / Catalog
          ↓
RunStockAnalysis
          ↓
AnalysisInputAssembler + Analysis Pipeline
          ↓
AnalysisResultStore
```

The market-wide capability should orchestrate existing application capabilities rather than duplicate their analysis logic.

## Alternatives Considered

### A — Add a `run_all()` method to `RunStockAnalysis`

**Idea:** Extend the existing single-stock use case so it accepts one or many stocks.

**Trade-offs:**

- fewer application classes;
- but weakens the single-stock use-case boundary;
- introduces two orchestration responsibilities into one component;
- makes the existing use case harder to reason about and test.

**Current assessment:** Not selected for the initial design direction.

### B — Create a dedicated market-wide application use case

Conceptually:

```
RunMarketAnalysis
    ↓
StockCatalog
    ↓
RunStockAnalysis
```

**Trade-offs:**

- explicit responsibility;
- preserves the single-stock boundary;
- easy to test aggregate semantics independently;
- introduces one additional application component.

**Current assessment:** Preferred candidate for further design.

### C — Put market-wide orchestration in the scheduler

**Idea:** The scheduler directly discovers stocks and executes analysis.

**Trade-offs:**

- convenient for the scheduled path;
- couples scheduling to business execution semantics;
- prevents manual/API callers from reusing the same market-wide capability;
- makes testing harder.

**Current assessment:** Not selected.

### D — Put orchestration in the dashboard/API

**Idea:** The client calls the single-symbol endpoint repeatedly.

**Trade-offs:**

- simple client implementation;
- creates transport-level orchestration;
- duplicates workflow knowledge in clients;
- poor fit for scheduled/background execution;
- makes partial failure semantics a client concern.

**Current assessment:** Not selected.

## Open Questions

These must be answered before implementation:

1. **Universe source:** Should the first MVP accept an explicit list of stocks, use `StockCatalog`, or introduce a separate universe abstraction?
2. **Failure semantics:** Should the aggregate execution be `COMPLETED`, `PARTIALLY_COMPLETED`, or `FAILED` when only some symbols fail?
3. **Ordering:** Is deterministic catalog ordering required?
4. **Empty universe:** What should happen when the requested universe is empty?
5. **Persistence:** Should successful stocks be persisted immediately as they complete, or only after the aggregate run finishes?
6. **Retry ownership:** Should existing per-stock retry semantics remain entirely inside `RunStockAnalysis`?
7. **Execution identity:** Should the aggregate run have its own execution identity separate from the existing per-stock execution?
8. **Concurrency:** The first MVP should remain sequential unless evidence establishes a need for concurrency.

## Proposed Invariants

The design should preserve these invariants unless evidence changes them:

1. One stock failure must not silently erase successful results for other stocks.
2. Per-stock analysis rules remain owned by the existing single-stock capability.
3. Market-wide orchestration must not calculate technical/fundamental scores itself.
4. Provider-specific behavior must remain behind infrastructure boundaries.
5. Successful per-stock persistence remains behind `AnalysisResultStore`.
6. Aggregate status must be derived from explicit per-stock outcomes.
7. The first implementation should be deterministic and sequential.

## TDD Acceptance Shape

Before implementation, tests should establish behavior for at least:

- empty universe;
- one-stock success;
- multiple-stock success;
- one failure with other successes;
- all stocks failing;
- unknown/missing stock handling;
- deterministic execution ordering;
- successful result persistence;
- reuse of existing single-stock analysis behavior;
- aggregate execution result semantics.

## Design Gate Decision

**Status: Proposed — implementation is not authorized by this document yet.**

The next action is to resolve the open questions and record the accepted decision before writing the M14 implementation.

## Consequences if Accepted

If this gate is accepted, the likely implementation boundary becomes:

```
RunMarketAnalysis
      ↓
StockCatalog
      ↓
RunStockAnalysis
      ↓
AnalysisResultStore
```

The API, dashboard, scheduler, ranking, and notification layers remain consumers of this application capability rather than owners of market-wide analysis semantics.

## Revisit Conditions

Revisit this gate if:

- the stock-universe model changes materially;
- persistent historical analysis becomes the next requirement;
- concurrency becomes an operational requirement;
- distributed execution becomes necessary;
- the scheduler requires different execution semantics;
- the analysis pipeline can no longer be safely reused per stock.
